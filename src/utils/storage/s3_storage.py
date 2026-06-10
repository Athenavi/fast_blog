"""
本地文件存储服务
提供文件存储与访问功能，兼容原 s3_storage 接口
"""
import os
from pathlib import Path
from typing import Optional


class S3Storage:
    """本地文件存储（兼容原 S3 接口）"""

    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload_fileobj(self, fileobj, key: str) -> bool:
        """上传文件对象（兼容 S3 接口）"""
        full_path = self.base_path / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = fileobj.read()
        with open(full_path, "wb") as f:
            f.write(content)
        return True

    async def delete_file(self, key: str) -> bool:
        """删除文件"""
        full_path = self.base_path / key
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def file_exists(self, key: str) -> bool:
        """检查文件是否存在"""
        return (self.base_path / key).exists()

    def get_file_url(self, key: str) -> str:
        """获取文件 URL"""
        return f"/api/v2/assets/storage/{key}"

    def save_file(self, file_hash: str, file_data: bytes, original_filename: str) -> str:
        """保存文件到存储（同步，兼容 FileProcessor.save_file 调用）"""
        _, ext = os.path.splitext(original_filename)
        key = f"{file_hash[:2]}/{file_hash}{ext}"
        full_path = self.base_path / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_data)
        return key

    async def download_file(self, key: str) -> Optional[bytes]:
        """下载文件内容"""
        full_path = self.base_path / key
        if not full_path.exists():
            return None
        with open(full_path, "rb") as f:
            return f.read()


# 全局实例
s3_storage = S3Storage()
