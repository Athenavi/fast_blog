"""
S3兼容存储实现类
支持AWS S3、MinIO、阿里云OSS、腾讯云COS等S3兼容服务
当S3不可用时，自动切换到本地存储

建议安装 boto3-stubs 以改善代码洞察体验：
pip install boto3-stubs
"""

import os
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError


class S3Storage:
    """
    S3兼容存储实现类
    支持AWS S3、MinIO、阿里云OSS、腾讯云COS等S3兼容服务
    当S3不可用时，自动切换到本地存储
    """

    def __init__(self, app=None):
        self.app = app
        self.s3_client = None  # 初始化时先设为None
        self.use_local_fallback = True  # 是否启用本地备用存储

        # 初始化默认配置值
        self.local_storage_path = 'storage'  # 设置默认值

        # 初始化S3相关配置为None
        self.s3_enabled = None
        self.s3_endpoint = None
        self.s3_access_key = None
        self.s3_secret_key = None
        self.s3_bucket_name = None
        self.s3_region = None
        self.s3_use_ssl = None
        self.s3_signature_version = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化应用配置"""
        self.app = app

        # S3配置 - 现在默认启用
        self.s3_enabled = app.config.get('S3_ENABLED', True) if hasattr(app, 'config') else True

        # 获取配置值 - 兼容FastAPI环境
        try:
            from src.setting import app_config
            self.s3_endpoint = getattr(app_config, 'S3_ENDPOINT_URL', None)
            self.s3_access_key = getattr(app_config, 'S3_ACCESS_KEY', None)
            self.s3_secret_key = getattr(app_config, 'S3_SECRET_KEY', None)
            self.s3_bucket_name = getattr(app_config, 'S3_BUCKET_NAME', 'media-bucket')
            self.s3_region = getattr(app_config, 'S3_REGION', 'us-east-1')
            self.s3_use_ssl = getattr(app_config, 'S3_USE_SSL', True)
            self.s3_signature_version = getattr(app_config, 'S3_SIGNATURE_VERSION', 's3v4')

            # 本地存储路径配置
            self.local_storage_path = getattr(app_config, 'LOCAL_STORAGE_PATH', 'storage')
        except ImportError:
            # 如果在Flask环境中，使用app.config
            self.s3_endpoint = app.config.get('S3_ENDPOINT_URL')
            self.s3_access_key = app.config.get('S3_ACCESS_KEY')
            self.s3_secret_key = app.config.get('S3_SECRET_KEY')
            self.s3_bucket_name = app.config.get('S3_BUCKET_NAME', 'media-bucket')
            self.s3_region = app.config.get('S3_REGION', 'us-east-1')
            self.s3_use_ssl = app.config.get('S3_USE_SSL', True)
            self.s3_signature_version = app.config.get('S3_SIGNATURE_VERSION', 's3v4')

            # 本地存储路径配置
            self.local_storage_path = app.config.get('LOCAL_STORAGE_PATH', 'storage')

        # 创建S3客户端
        self.s3_client = self._create_s3_client()

        # 创建本地存储目录
        os.makedirs(self.local_storage_path, exist_ok=True)

    def _create_s3_client(self):
        """创建S3客户端"""
        if not self.s3_enabled:
            print("提示: S3存储被禁用，将使用本地存储")
            return None

        # 检查必要的配置
        if not all([self.s3_access_key, self.s3_secret_key, self.s3_bucket_name]):
            print("警告: S3配置不完整，将使用本地存储")
            print(f"S3_ACCESS_KEY: {'已配置' if self.s3_access_key else '未配置'}")
            print(f"S3_SECRET_KEY: {'已配置' if self.s3_secret_key else '未配置'}")
            print(f"S3_BUCKET_NAME: {'已配置' if self.s3_bucket_name else '未配置'}")
            return None

        # 配置S3客户端参数
        client_config = {
            'aws_access_key_id': self.s3_access_key,
            'aws_secret_access_key': self.s3_secret_key,
            'region_name': self.s3_region,
        }

        # 如果有自定义端点（如MinIO），添加endpoint_url
        if self.s3_endpoint and self.s3_endpoint.strip():
            client_config['endpoint_url'] = self.s3_endpoint
            client_config['use_ssl'] = self.s3_use_ssl
            # 只有在使用SSL时才设置verify
            if self.s3_use_ssl:
                client_config['verify'] = True  # 对于自签名证书可以设为False，但默认设为True

        # 创建S3客户端
        try:
            s3_client = boto3.client('s3', **client_config)
        except Exception as e:
            print(f"创建S3客户端失败: {e}")
            print("将使用本地存储作为备选方案")
            return None

        # 验证连接
        try:
            s3_client.head_bucket(Bucket=self.s3_bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # 存储桶不存在，尝试创建
                try:
                    if self.s3_region == 'us-east-1':
                        # us-east-1区域创建存储桶不需要LocationConstraint
                        s3_client.create_bucket(Bucket=self.s3_bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=self.s3_bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.s3_region}
                        )
                    print(f"S3存储桶 {self.s3_bucket_name} 创建成功")
                except ClientError as create_error:
                    print(f"无法创建S3存储桶: {create_error}")
                    print("将使用本地存储作为备选方案")
                    return None
            else:
                print(f"无法访问S3存储桶: {e}")
                print("将使用本地存储作为备选方案")
                return None

        return s3_client

    def _ensure_s3_client(self):
        """确保S3客户端已初始化"""
        if self.s3_client is None:
            try:
                from src.setting import app_config
                # 如果没有初始化，尝试从配置初始化
                self.s3_enabled = getattr(app_config, 'S3_ENABLED', True)
                self.s3_endpoint = getattr(app_config, 'S3_ENDPOINT_URL', None)
                self.s3_access_key = getattr(app_config, 'S3_ACCESS_KEY', None)
                self.s3_secret_key = getattr(app_config, 'S3_SECRET_KEY', None)
                self.s3_bucket_name = getattr(app_config, 'S3_BUCKET_NAME', 'media-bucket')
                self.s3_region = getattr(app_config, 'S3_REGION', 'us-east-1')
                self.s3_use_ssl = getattr(app_config, 'S3_USE_SSL', True)
                self.s3_signature_version = getattr(app_config, 'S3_SIGNATURE_VERSION', 's3v4')

                self.s3_client = self._create_s3_client()
            except Exception as e:
                print(f"初始化S3客户端失败: {e}")
                print("将使用本地存储作为备选方案")
                self.s3_client = None

    def save_file(self, file_hash: str, file_data: bytes, original_filename: str) -> str:
        """
        保存文件到S3存储，如果S3不可用则保存到本地存储
        返回存储路径（格式：s3://bucket/key 或 local://path）
        """
        # 尝试使用S3存储
        if self.s3_client is not None:
            try:
                # 构建S3对象键（路径）
                # 使用哈希的前两个字符作为目录，提高性能
                hash_prefix = file_hash[:2]
                key = f"objects/{hash_prefix}/{file_hash}"

                # 上传文件到S3
                self.s3_client.put_object(
                    Bucket=self.s3_bucket_name,
                    Key=key,
                    Body=file_data,
                    Metadata={
                        'original_filename': original_filename,
                        'file_hash': file_hash
                    }
                )

                # 返回S3路径格式
                storage_path = f"s3://{self.s3_bucket_name}/{key}"
                return storage_path

            except Exception as e:
                print(f"S3文件上传失败: {str(e)}")
                print("切换到本地存储...")
        # S3不可用时，使用本地存储
        return self._save_to_local(file_hash, file_data, original_filename)

    def _save_to_local(self, file_hash: str, file_data: bytes, original_filename: str) -> str:
        """
        保存文件到本地存储
        """
        try:
            # 使用哈希的前两个字符作为目录，提高性能
            hash_prefix = file_hash[:2]
            local_dir = os.path.join(self.local_storage_path, 'objects', hash_prefix)
            os.makedirs(local_dir, exist_ok=True)

            # 构建完整的文件路径
            local_file_path = os.path.join(local_dir, file_hash)

            # 写入文件
            with open(local_file_path, 'wb') as f:
                f.write(file_data)

            # 返回本地路径格式
            storage_path = f"local://{os.path.abspath(local_file_path)}"
            return storage_path

        except Exception as e:
            print(f"本地文件保存失败: {str(e)}")
            raise

    def load_file(self, storage_path: str) -> Optional[bytes]:
        """
        从存储加载文件（S3或本地）
        """
        if storage_path.startswith('s3://'):
            # 从S3加载文件
            try:
                # 确保S3客户端已初始化
                self._ensure_s3_client()

                if self.s3_client is None:
                    print("S3客户端不可用，无法加载S3文件")
                    return None

                # 解析S3路径
                parsed = urlparse(storage_path)
                bucket = parsed.netloc
                key = parsed.path.lstrip('/')

                # 从S3下载文件
                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                file_data = response['Body'].read()
                return file_data

            except ClientError as e:
                print(f"从S3加载文件失败: {str(e)}")
                return None
            except Exception as e:
                print(f"从S3加载文件失败: {str(e)}")
                return None

        elif storage_path.startswith('local://'):
            # 从本地加载文件
            try:
                # 解析本地路径
                local_path = storage_path.replace('local://', '', 1)

                # 读取文件
                with open(local_path, 'rb') as f:
                    file_data = f.read()
                return file_data

            except FileNotFoundError:
                print(f"本地文件不存在: {storage_path}")
                return None
            except Exception as e:
                print(f"从本地加载文件失败: {str(e)}")
                return None

        else:
            print(f"错误: 未知的存储路径格式: {storage_path}")
            return None

    def delete_file(self, storage_path: str) -> bool:
        """
        从存储删除文件（S3或本地）
        """
        if storage_path.startswith('s3://'):
            # 从S3删除文件
            try:
                # 确保S3客户端已初始化
                self._ensure_s3_client()

                if self.s3_client is None:
                    print("S3客户端不可用，无法删除S3文件")
                    return False

                # 解析S3路径
                parsed = urlparse(storage_path)
                bucket = parsed.netloc
                key = parsed.path.lstrip('/')

                # 从S3删除文件
                self.s3_client.delete_object(Bucket=bucket, Key=key)
                return True

            except ClientError as e:
                print(f"从S3删除文件失败: {str(e)}")
                return False
            except Exception as e:
                print(f"从S3删除文件失败: {str(e)}")
                return False

        elif storage_path.startswith('local://'):
            # 从本地删除文件
            try:
                # 解析本地路径
                local_path = storage_path.replace('local://', '', 1)

                # 删除文件
                if os.path.exists(local_path):
                    os.remove(local_path)

                    # 尝试删除空的父目录
                    parent_dir = os.path.dirname(local_path)
                    if os.path.isdir(parent_dir):
                        try:
                            # 检查目录是否为空
                            if not os.listdir(parent_dir):
                                os.rmdir(parent_dir)
                        except OSError:
                            pass  # 忽略删除非空目录的错误
                    return True
                else:
                    print(f"本地文件不存在，无法删除: {storage_path}")
                    return False

            except Exception as e:
                print(f"从本地删除文件失败: {str(e)}")
                return False

        else:
            print(f"错误: 未知的存储路径格式: {storage_path}")
            return False

    def file_exists(self, storage_path: str) -> bool:
        """
        检查文件是否存在（S3或本地）
        """
        if storage_path.startswith('s3://'):
            # 检查S3中文件是否存在
            try:
                # 确保S3客户端已初始化
                self._ensure_s3_client()

                if self.s3_client is None:
                    print("S3客户端不可用，无法检查S3文件存在性")
                    return False

                # 解析S3路径
                parsed = urlparse(storage_path)
                bucket = parsed.netloc
                key = parsed.path.lstrip('/')

                # 检查S3中文件是否存在
                self.s3_client.head_object(Bucket=bucket, Key=key)
                return True

            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                else:
                    print(f"检查S3文件存在性失败: {str(e)}")
                    return False
            except Exception as e:
                print(f"检查S3文件存在性失败: {str(e)}")
                return False

        elif storage_path.startswith('local://'):
            # 检查本地文件是否存在
            try:
                # 解析本地路径
                local_path = storage_path.replace('local://', '', 1)

                # 检查文件是否存在
                return os.path.exists(local_path)

            except Exception as e:
                print(f"检查本地文件存在性失败: {str(e)}")
                return False

        else:
            print(f"错误: 未知的存储路径格式: {storage_path}")
            return False

    def get_file_url(self, storage_path: str, expires: int = 3600) -> Optional[str]:
        """
        生成文件的访问URL（S3或本地）
        """
        if storage_path.startswith('s3://'):
            # 生成S3文件的预签名URL（用于临时访问）
            try:
                # 确保S3客户端已初始化
                self._ensure_s3_client()

                if self.s3_client is None:
                    print("S3客户端不可用，无法生成S3预签名URL")
                    return None

                # 解析S3路径
                parsed = urlparse(storage_path)
                bucket = parsed.netloc
                key = parsed.path.lstrip('/')

                # 生成预签名URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=expires
                )
                return url

            except Exception as e:
                print(f"生成S3预签名URL失败: {str(e)}")
                return None

        elif storage_path.startswith('local://'):
            # 对于本地文件，返回一个特殊的访问路径
            # 这需要配合Web服务器的静态文件服务
            try:
                # 解析本地路径
                local_path = storage_path.replace('local://', '', 1)

                # 生成一个相对路径，供Web服务器使用
                # 例如，如果本地路径是 /var/www/storage/objects/ab/hash_value
                # 则返回 /local-storage/hashed_files/ab/hash_value
                rel_path = os.path.relpath(local_path, self.local_storage_path)
                # 确保路径分隔符正确（特别是在Windows上）
                rel_path = rel_path.replace(os.sep, '/')
                return f"/local-storage/{rel_path}"

            except Exception as e:
                print(f"生成本地文件URL失败: {str(e)}")
                return None

        else:
            print(f"错误: 未知的存储路径格式: {storage_path}")
            return None


# 全局S3存储实例
s3_storage = S3Storage()


