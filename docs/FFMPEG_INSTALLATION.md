# FFmpeg 安装指南

FastBlog 使用 FFmpeg 进行视频处理，包括：

- 视频缩略图提取
- 视频转码（多种分辨率）
- 音频提取
- GIF转换

## Windows 安装

### 方法1：使用 Scoop（推荐）

```powershell
# 安装 Scoop
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# 安装 FFmpeg
scoop install ffmpeg
```

### 方法2：手动下载

1. 访问 [FFmpeg 官网](https://ffmpeg.org/download.html)
2. 点击 "Windows" -> "Windows builds by BtbN"
3. 下载最新版本的 `ffmpeg-master-latest-win64-gpl.zip`
4. 解压到任意目录，例如：`C:\ffmpeg`
5. 将 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量

或者在 `.env` 文件中配置：

```env
FFMPEG_PATH=C:/ffmpeg/bin/ffmpeg.exe
FFPROBE_PATH=C:/ffmpeg/bin/ffprobe.exe
```

### 验证安装

打开命令提示符或 PowerShell：

```powershell
ffmpeg -version
ffprobe -version
```

如果显示版本信息，说明安装成功。

## Linux 安装

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

### CentOS/RHEL

```bash
sudo yum install epel-release
sudo yum install ffmpeg ffmpeg-devel
```

或使用 RPM Fusion：

```bash
sudo dnf install https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
sudo dnf install ffmpeg
```

### Arch Linux

```bash
sudo pacman -S ffmpeg
```

### 验证安装

```bash
ffmpeg -version
ffprobe -version
```

## macOS 安装

### 使用 Homebrew（推荐）

```bash
# 安装 Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 FFmpeg
brew install ffmpeg
```

### 验证安装

```bash
ffmpeg -version
ffprobe -version
```

## Docker 环境

如果使用 Docker，可以在 Dockerfile 中添加：

```dockerfile
FROM python:3.11-slim

# 安装 FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# ... 其他配置
```

或在 docker-compose.yml 中：

```yaml
services:
  app:
    image: your-image
    # FFmpeg 已包含在镜像中
```

## 配置 FastBlog

安装完成后，在 `.env` 文件中配置（如果 ffmpeg 在 PATH 中，可以跳过此步骤）：

```env
# FFmpeg 路径配置
FFMPEG_PATH=ffmpeg  # 如果在 PATH 中
# 或者指定完整路径：
# FFMPEG_PATH=/usr/bin/ffmpeg  # Linux
# FFMPEG_PATH=C:/ffmpeg/bin/ffmpeg.exe  # Windows

FFPROBE_PATH=ffprobe  # 通常与 ffmpeg 在同一目录
```

## 测试视频处理功能

上传一个视频文件到 FastBlog 媒体库，系统会自动：

1. 提取视频信息（时长、分辨率等）
2. 生成缩略图（从第1秒提取）
3. 更新媒体记录

检查日志确认处理是否成功：

```
INFO: 开始处理视频文件: video.mp4
INFO: 视频信息: {'duration': 120.5, 'width': 1920, 'height': 1080, ...}
INFO: 成功创建视频缩略图: storage/thumbnails/xxx_thumb.jpg
INFO: 视频处理完成: video.mp4
```

## 常见问题

### 1. "FFmpeg 未安装或不可用"

**原因**：FFmpeg 未正确安装或不在 PATH 中

**解决方案**：

- 确认已安装 FFmpeg
- 检查 PATH 环境变量
- 或在 `.env` 中指定完整路径

### 2. 视频处理失败

**可能原因**：

- 视频格式不支持
- 文件损坏
- 权限问题

**解决方案**：

- 检查日志获取详细错误信息
- 尝试使用其他视频文件
- 确保存储目录有写入权限

### 3. 处理速度慢

**优化建议**：

- 使用更快的预设：修改 `video_processor.py` 中的 `preset='fast'` 或 `'ultrafast'`
- 降低输出质量：增加 CRF 值（默认23，可调整为25-28）
- 限制最大分辨率

## 性能优化建议

### 转码预设选择

x264 预设速度从快到慢：

- `ultrafast` - 最快，文件最大
- `superfast`
- `veryfast`
- `faster`
- `fast` - 推荐用于实时处理
- `medium` - 默认，平衡速度和质量
- `slow`
- `slower`
- `veryslow` - 最慢，文件最小

### CRF 质量因子

恒定质量因子（CRF）范围：0-51

- 18-20：高质量（文件较大）
- 23：默认值（推荐）
- 25-28：较低质量（文件较小）

数值越小，质量越高，文件越大。

## 高级功能

### 批量处理现有视频

可以编写脚本批量处理已上传的视频：

```python
from shared.models import Media, FileHash
from src.utils.image.video_processor import video_processor
from sqlalchemy import select

# 查询所有视频文件
query = select(Media).where(Media.file_type == 'video')
videos = db.execute(query).scalars().all()

for media in videos:
    if not media.thumbnail_path:
        # 处理视频
        process_video(media)
```

### 自定义转码配置

修改 `public_upload.py` 中的 `_process_video_after_upload` 方法，启用多分辨率转码：

```python
# 取消注释以下代码以启用多分辨率转码
resolution_results = video_processor.generate_multiple_resolutions(
    input_path=local_video_path,
    output_dir=resolutions_dir
)
```

## 资源链接

- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)
- [FFmpeg 命令大全](https://ffmpeg.org/ffmpeg.html)
- [H.264 编码指南](https://trac.ffmpeg.org/wiki/Encode/H.264)
