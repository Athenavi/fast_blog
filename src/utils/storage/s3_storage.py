"""
存储管理模块 - S3/本地存储抽象层
"""
from pathlib import Path
from typing import Optional


class LocalStorage:
    """本地存储实现"""

    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_hash: str, file_data: bytes, original_filename: str) -> str:
        """保存文件到本地存储"""
        # 使用哈希前两位作为子目录，避免单目录文件过多
        subdir = file_hash[:2]
        ext = Path(original_filename).suffix or '.bin'
        filename = f"{file_hash}{ext}"
        storage_path = f"objects/{subdir}/{filename}"

        full_path = self.base_path / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'wb') as f:
            f.write(file_data)

        return storage_path

    def save_raw_file(self, storage_path: str, file_data: bytes) -> bool:
        """保存原始文件数据"""
        full_path = self.base_path / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, 'wb') as f:
                f.write(file_data)
            return True
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False

    def read_file(self, storage_path: str) -> Optional[bytes]:
        """读取文件内容"""
        full_path = self.base_path / storage_path

        if not full_path.exists():
            return None

        try:
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"读取文件失败: {e}")
            return None

    def delete_file(self, storage_path: str) -> bool:
        """删除文件"""
        full_path = self.base_path / storage_path

        try:
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False

    def file_exists(self, storage_path: str) -> bool:
        """检查文件是否存在"""
        full_path = self.base_path / storage_path
        return full_path.exists()


# 全局实例 - 默认使用本地存储
# 如果需要使用S3，可以在此处切换为 S3Storage 实例
s3_storage = LocalStorage()
