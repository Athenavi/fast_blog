"""音频元数据提取（封面 / 歌词）

自 v2 ``media_legacy/routes_audio_metadata.py`` 平移（T5-10：v2 → v3 收敛），
提取逻辑保持一致：封面取内嵌图转 base64，歌词取 ID3 USLT 帧 + 同名 .lrc 文件。

v2 里的 ``find_lrc_file`` / ``parse_lrc_file`` 是无人调用的死代码，未移植。
"""

import base64
import re
from pathlib import Path
from typing import Optional

from shared.config import settings
from src.api.v3.core.logger import get_logger

logger = get_logger("mobile-media")


def build_audio_metadata(media) -> dict:
    """组装音频元数据响应（形状与 v2 完全一致，前端 ``useAudioMetadata`` 依赖它）"""
    result = {
        "cover_image": None,  # base64 编码的封面图片
        "lyrics": [],  # 歌词数组 [{time: 秒, text: 文本}]
        "title": media.original_filename,
        "duration": media.duration,
    }

    cover_data = extract_cover_from_audio(media)
    if cover_data:
        cover_base64 = base64.b64encode(cover_data).decode("utf-8")
        mime_type = detect_image_mime_type(cover_data)
        result["cover_image"] = f"data:{mime_type};base64,{cover_base64}"
        logger.info(f"成功提取音频封面: media_id={media.id}")

    lyrics = extract_lyrics_from_audio(media)
    if lyrics:
        result["lyrics"] = lyrics
        logger.info(f"成功提取音频歌词: media_id={media.id}, 共{len(lyrics)}条")

    return result


def extract_cover_from_audio(media) -> Optional[bytes]:
    """从音频文件中提取封面图片"""
    try:
        from src.utils.image.audio_processor import extract_audio_cover

        file_path = media.file_path
        if not file_path:
            return None

        # S3 路径：先下载到临时文件再提取
        if file_path.startswith("s3://"):
            try:
                import os
                import tempfile

                import boto3

                parts = file_path.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""

                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                    aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                    region_name=getattr(settings, "AWS_REGION", "us-east-1"),
                )

                with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp_file:
                    s3_client.download_file(bucket, key, tmp_file.name)
                    result = extract_audio_cover(tmp_file.name)

                os.unlink(tmp_file.name)
                return result
            except Exception as e:
                logger.error(f"S3文件下载失败: {e}")
                return None

        # 本地文件直接提取（防御路径遍历）
        candidate_path = (Path("storage") / file_path.lstrip("/")).resolve()
        if not str(candidate_path).startswith(str(Path("storage").resolve())):
            logger.warning(f"路径逃逸被拒绝: {file_path}")
            return None
        if candidate_path.exists():
            return extract_audio_cover(str(candidate_path))

        logger.warning(f"音频文件不存在: {candidate_path}")
        return None

    except ImportError:
        logger.error("mutagen库未安装")
        return None
    except Exception as e:
        logger.error(f"提取封面失败: {e}")
        return None


def extract_lyrics_from_audio(media) -> list:
    """从音频文件中提取歌词（ID3 标签 + 同名 .lrc 文件）"""
    all_lyrics: list = []

    try:
        lyrics = extract_lyrics_from_id3(media)
        if lyrics:
            all_lyrics.extend(lyrics)
    except Exception as e:
        logger.error(f"从ID3提取歌词失败: {e}")

    try:
        import os

        file_path = media.file_path
        if file_path and not file_path.startswith("s3://"):
            file_path_actual = str(Path("storage/") / file_path)
            if os.path.exists(file_path_actual):
                lrc_path = os.path.splitext(file_path_actual)[0] + ".lrc"
                if os.path.exists(lrc_path):
                    with open(lrc_path, "r", encoding="utf-8") as f:
                        lrc_content = f.read()
                    all_lyrics.extend(parse_lrc_text(lrc_content))
    except Exception as e:
        logger.warning(f"加载LRC歌词文件失败: {e}")

    if all_lyrics:
        all_lyrics.sort(key=lambda x: x["time"])

    return all_lyrics


def extract_lyrics_from_id3(media) -> list:
    """从音频文件的 ID3 标签中提取 USLT 帧（同步歌词）"""
    try:
        from mutagen import File as MutagenFile
        from mutagen.id3 import USLT
        from mutagen.mp3 import MP3

        file_path = media.file_path
        if not file_path:
            return []

        if file_path.startswith("s3://"):
            logger.warning("S3存储的音频文件暂不支持歌词提取")
            return []

        full_path = Path("storage/") / file_path
        if not full_path.exists():
            logger.warning(f"音频文件不存在: {full_path}")
            return []

        # 安全限制：拒绝超过 1MB 的 ID3 标签
        max_id3_size = 1 * 1024 * 1024
        file_stat = full_path.stat()
        lower_path = file_path.lower()

        if lower_path.endswith(".mp3"):
            # MP3 的 ID3v2 标签位于文件开头
            if file_stat.st_size > max_id3_size * 2:
                with open(full_path, "rb") as fh:
                    header = fh.read(10)
                if header[:3] == b"ID3":
                    id3_size = (
                        (header[6] & 0x7F) << 21
                        | (header[7] & 0x7F) << 14
                        | (header[8] & 0x7F) << 7
                        | (header[9] & 0x7F)
                    )
                    if id3_size > max_id3_size:
                        logger.warning(f"ID3 标签过大 ({id3_size} bytes)，跳过歌词提取")
                        return []
        else:
            # 通用格式：文件整体小于 1MB 才尝试标签提取
            if file_stat.st_size > max_id3_size:
                logger.warning(f"文件过大 ({file_stat.st_size} bytes)，跳过通用音频标签提取")
                return []

        if lower_path.endswith(".mp3"):
            audio_file = MP3(str(full_path))
        else:
            audio_file = MutagenFile(str(full_path))

        if not audio_file or not hasattr(audio_file, "tags"):
            logger.debug(f"音频文件没有ID3标签: {file_path}")
            return []

        lyrics_list: list = []
        for tag in audio_file.tags.values():
            if isinstance(tag, USLT):
                lyric_text = tag.text
                if lyric_text:
                    parsed_lyrics = parse_lrc_text(lyric_text)
                    if parsed_lyrics:
                        lyrics_list.extend(parsed_lyrics)
                    else:
                        lyrics_list.append({"time": 0.0, "text": lyric_text.strip()})
                    logger.info(f"从ID3标签提取到歌词: {len(lyric_text)} 字符")

        if lyrics_list:
            lyrics_list.sort(key=lambda x: x["time"])
            logger.info(f"成功从ID3标签提取歌词: {len(lyrics_list)} 条")

        return lyrics_list

    except ImportError:
        logger.error("mutagen库未安装")
        return []
    except Exception as e:
        logger.error(f"从ID3提取歌词失败: {e}")
        return []


def parse_lrc_text(text: str) -> list:
    """解析包含 LRC 时间戳的歌词文本（[mm:ss.xx]歌词）"""
    lyrics: list = []
    max_lyrics_lines = 500  # 最大解析行数限制

    for line in text.split("\n"):
        if len(lyrics) >= max_lyrics_lines:
            logger.warning(f"歌词行数超过限制 ({max_lyrics_lines})，截断多余行")
            break

        line = line.strip()
        if not line:
            continue

        matches = re.findall(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)", line)
        for match in matches:
            minutes = int(match[0])
            seconds = int(match[1])
            milliseconds = int(match[2].ljust(3, "0"))  # 补齐 3 位
            lyric_text = match[3].strip()

            if lyric_text:
                time_in_seconds = minutes * 60 + seconds + milliseconds / 1000
                lyrics.append({"time": round(time_in_seconds, 2), "text": lyric_text})

    return lyrics


def detect_image_mime_type(image_data: bytes) -> str:
    """检测图片数据的 MIME 类型（按文件头）"""
    if len(image_data) < 4:
        return "image/jpeg"

    if image_data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_data[:4] == b"\x89PNG":
        return "image/png"
    if image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        return "image/webp"
    if image_data[:2] == b"BM":
        return "image/bmp"
    return "image/jpeg"
