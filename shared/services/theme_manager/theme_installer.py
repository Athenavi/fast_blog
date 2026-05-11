"""
主题安装服务
支持ZIP包上传安装、依赖检查、版本验证
"""

import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from shared.services.theme_manager.theme_system import theme_manager

# 常量定义
VERSION_FILE = Path(__file__).parent.parent.parent / 'version.txt'
REQUIRED_METADATA_FIELDS = ['name', 'slug', 'version']


class ThemeInstaller:
    """
    主题安装器
    
    功能:
    1. ZIP包解压安装
    2. 依赖检查
    3. 版本兼容性验证
    4. 完整性校验
    """

    def __init__(self):
        self.themes_dir = theme_manager.themes_dir

    def install_from_zip(self, zip_path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        从ZIP文件安装主题
        
        Args:
            zip_path: ZIP文件路径
            
        Returns:
            (成功标志, 消息, 主题元数据)
        """
        try:
            zip_file = Path(zip_path)

            if not zip_file.exists():
                return False, f"ZIP文件不存在: {zip_path}", None

            if not zipfile.is_zipfile(zip_file):
                return False, "无效的主题ZIP文件", None

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # 解压并安全检查
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    for member in zip_ref.namelist():
                        member_path = temp_path / member
                        if not str(member_path.resolve()).startswith(str(temp_path.resolve())):
                            return False, f"不安全的路径: {member}", None
                    zip_ref.extractall(temp_path)

                # 查找主题目录
                theme_dir = self._find_theme_directory(temp_path)
                if not theme_dir:
                    return False, "无法找到主题目录结构", None

                # 读取并验证metadata.json
                metadata_file = theme_dir / "metadata.json"
                if not metadata_file.exists():
                    return False, "缺少metadata.json文件", None

                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # 验证必需字段
                for field in REQUIRED_METADATA_FIELDS:
                    if field not in metadata:
                        return False, f"缺少必需字段: {field}", None

                slug = metadata['slug']

                # 检查是否已安装
                if (self.themes_dir / slug).exists():
                    return False, f"主题 '{slug}' 已安装", None

                # 版本兼容性检查
                compatibility_result = self.check_compatibility(metadata)
                if not compatibility_result[0]:
                    return False, compatibility_result[1], None

                # 移动到主题目录
                shutil.copytree(theme_dir, self.themes_dir / slug)

                return True, f"主题 '{metadata['name']}' 安装成功", metadata

        except zipfile.BadZipFile:
            return False, "损坏的ZIP文件", None
        except Exception as e:
            return False, f"安装失败: {str(e)}", None

    def _find_theme_directory(self, extract_path: Path) -> Optional[Path]:
        """
        在解压目录中查找主题根目录
        
        Args:
            extract_path: 解压后的目录
            
        Returns:
            主题目录路径
        """
        # 检查是否有metadata.json
        if (extract_path / "metadata.json").exists():
            return extract_path

        # 查找包含metadata.json的子目录
        for item in extract_path.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                return item

        return None

    def check_compatibility(self, metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查主题兼容性
            
        Args:
            metadata: 主题元数据
                
        Returns:
            (兼容标志, 消息)
        """
        requires = metadata.get('requires', {})
    
        # 检查FastBlog版本要求
        fastblog_version = requires.get('fastblog')
        if fastblog_version:
            try:
                current_version = self._get_current_version()
                if not self._check_version_compatibility(current_version, fastblog_version):
                    return False, f"需要 FastBlog 版本 {fastblog_version}，当前版本 {current_version}"
            except Exception as e:
                print(f"检查 FastBlog 版本失败: {e}")
    
        # 检查Python版本要求
        python_version = requires.get('python')
        if python_version:
            try:
                current_python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                if not self._check_version_compatibility(current_python, python_version):
                    return False, f"需要 Python 版本 {python_version}，当前版本 {current_python}"
            except Exception as e:
                print(f"检查 Python 版本失败: {e}")
    
        return True, "兼容性检查通过"

    def _get_current_version(self) -> str:
        """获取当前 FastBlog 版本"""
        if VERSION_FILE.exists():
            with open(VERSION_FILE, 'r') as f:
                return f.read().strip()
        return '0.0.1'
        
    def _check_version_compatibility(self, current_version: str, required_version: str) -> bool:
        """
        检查版本兼容性
            
        Args:
            current_version: 当前版本
            required_version: 要求的版本（支持 >=, >, = 等前缀）
                
        Returns:
            是否兼容
        """
        def parse_version(v: str) -> tuple:
            """解析版本号字符串为元组"""
            # 移除前缀如 >=, >, =
            v_clean = v.lstrip('>=<')
            parts = []
            for part in v_clean.split('.'):
                try:
                    parts.append(int(part))
                except ValueError:
                    parts.append(0)
            return tuple(parts)
            
        def compare_versions(v1: tuple, v2: tuple) -> int:
            """比较两个版本号
            Returns: -1 (v1<v2), 0 (v1==v2), 1 (v1>v2)
            """
            # 补齐长度
            max_len = max(len(v1), len(v2))
            v1 = v1 + (0,) * (max_len - len(v1))
            v2 = v2 + (0,) * (max_len - len(v2))
                
            for a, b in zip(v1, v2):
                if a < b:
                    return -1
                elif a > b:
                    return 1
            return 0
            
        # 解析版本
        current = parse_version(current_version)
            
        # 处理不同的版本要求格式
        if required_version.startswith('>='): 
            required = parse_version(required_version[2:])
            return compare_versions(current, required) >= 0
        elif required_version.startswith('>'):
            required = parse_version(required_version[1:])
            return compare_versions(current, required) > 0
        elif required_version.startswith('<='): 
            required = parse_version(required_version[2:])
            return compare_versions(current, required) <= 0
        elif required_version.startswith('<'):
            required = parse_version(required_version[1:])
            return compare_versions(current, required) < 0
        elif required_version.startswith('=') or required_version.startswith('=='): 
            required = parse_version(required_version.lstrip('='))
            return compare_versions(current, required) == 0
        else:
            # 默认精确匹配
            required = parse_version(required_version)
            return compare_versions(current, required) == 0

    def validate_theme_structure(self, theme_dir: Path) -> Tuple[bool, str]:
        """
        验证主题目录结构
        
        Args:
            theme_dir: 主题目录路径
            
        Returns:
            (有效标志, 消息)
        """
        if not theme_dir.exists() or not theme_dir.is_dir():
            return False, "主题目录不存在或不是目录"

        # 检查必需文件
        metadata_file = theme_dir / 'metadata.json'
        if not metadata_file.exists():
            return False, "缺少必需文件: metadata.json"

        # 验证metadata.json格式
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            for field in REQUIRED_METADATA_FIELDS:
                if field not in metadata:
                    return False, f"metadata.json缺少字段: {field}"

        except json.JSONDecodeError:
            return False, "metadata.json格式错误"

        return True, "主题结构验证通过"

    def uninstall_theme(self, theme_slug: str) -> Tuple[bool, str]:
        """
        卸载主题
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            (成功标志, 消息)
        """
        try:
            theme_dir = self.themes_dir / theme_slug

            if not theme_dir.exists():
                return False, f"主题 '{theme_slug}' 未安装"

            # 删除主题目录
            shutil.rmtree(theme_dir)

            return True, f"主题 '{theme_slug}' 已卸载"

        except Exception as e:
            return False, f"卸载失败: {str(e)}"

    def get_theme_info(self, theme_slug: str) -> Optional[Dict[str, Any]]:
        """
        获取主题详细信息
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            主题信息字典
        """
        theme_dir = self.themes_dir / theme_slug

        if not theme_dir.exists():
            return None

        metadata_file = theme_dir / "metadata.json"
        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # 添加额外信息
            metadata['path'] = str(theme_dir)
            metadata['slug'] = theme_slug

            # 检查截图
            screenshot = theme_dir / "screenshot.png"
            if screenshot.exists():
                metadata['has_screenshot'] = True
            else:
                metadata['has_screenshot'] = False

            return metadata

        except Exception as e:
            print(f"读取主题信息失败: {e}")
            return None


# 全局实例
theme_installer = ThemeInstaller()
