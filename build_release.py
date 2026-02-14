#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastBlog 发布构建脚本
负责打包整个项目为可发布的发行版本
支持从 Git 提交历史自动生成发布说明（含多行 body）
"""

import argparse
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_current_version():
    """获取当前版本号"""
    try:
        with open('version.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '1.0.0'


def get_backend_versions():
    """获取后端依赖版本信息"""
    versions = []

    # 获取Python版本
    versions.append(f"- Python版本: {platform.python_version()}")

    # 从requirements.txt读取主要依赖版本
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.readlines()

        important_packages = [
            'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic',
            'alembic', 'passlib', 'python-jose', 'python-multipart',
            'pillow', 'requests', 'aiofiles'
        ]

        found_packages = []
        for req in requirements:
            req = req.strip()
            if req and not req.startswith('#'):
                for package in important_packages:
                    if req.lower().startswith(package):
                        # 提取包名和版本
                        if '==' in req:
                            pkg_name, version = req.split('==', 1)
                            found_packages.append((pkg_name.strip(), version.strip()))
                        elif '>=' in req:
                            pkg_name, version = req.split('>=', 1)
                            found_packages.append((pkg_name.strip(), f">={version.strip()}"))
                        elif '<' in req:
                            pkg_name, version = req.split('<', 1)
                            found_packages.append((pkg_name.strip(), f"<{version.strip()}"))
                        else:
                            found_packages.append((req, 'latest'))
                        break

        # 按字母顺序排序
        found_packages.sort(key=lambda x: x[0].lower())
        for pkg_name, version in found_packages:
            versions.append(f"- {pkg_name}: {version}")

    except FileNotFoundError:
        versions.append("- 无法读取requirements.txt")
    except Exception as e:
        versions.append(f"- 读取依赖信息出错: {str(e)}")

    return versions


def get_frontend_versions():
    """获取前端依赖版本信息"""
    versions = []

    try:
        with open('frontend-next/package.json', 'r', encoding='utf-8') as f:
            package_data = json.load(f)

        # 获取核心框架版本
        core_deps = ['next', 'react', 'react-dom']
        for dep in core_deps:
            version = package_data.get('dependencies', {}).get(dep, 'unknown')
            if version != 'unknown':
                versions.append(f"- {dep.capitalize()}: {version}")

        # 获取开发依赖中的重要工具
        dev_tools = ['typescript', '@types/react', '@types/node']
        for dep in dev_tools:
            version = package_data.get('devDependencies', {}).get(dep) or \
                      package_data.get('dependencies', {}).get(dep, 'unknown')
            if version != 'unknown':
                versions.append(f"- {dep}: {version}")

        # 获取UI相关依赖
        ui_deps = ['tailwindcss', 'postcss', 'autoprefixer']
        for dep in ui_deps:
            version = package_data.get('devDependencies', {}).get(dep) or \
                      package_data.get('dependencies', {}).get(dep)
            if version:
                versions.append(f"- {dep}: {version}")

    except FileNotFoundError:
        versions.append("- 无法读取package.json")
    except json.JSONDecodeError:
        versions.append("- package.json格式错误")
    except Exception as e:
        versions.append(f"- 读取前端依赖出错: {str(e)}")

    return versions


def format_version_list(versions):
    """格式化版本列表为字符串"""
    if not versions:
        return "- 暂无版本信息"
    return '\n'.join(versions)


class ReleaseBuilder:
    """发布构建器"""

    def __init__(self, version: str, output_dir: str = "release"):
        self.version = version
        self.output_dir = Path(output_dir)
        self.project_root = Path(__file__).resolve().parent
        self.build_temp = Path(tempfile.mkdtemp(prefix="fastblog_build_"))
        self.release_dir = self.output_dir / f"fastblog-v{version}"

        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)
        self.release_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"构建版本: {version}")
        logger.info(f"项目根目录: {self.project_root}")
        logger.info(f"发布目录: {self.release_dir}")

    def get_file_hash(self, file_path: Path) -> str:
        """计算文件SHA256哈希值"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def copy_backend_files(self) -> List[Path]:
        """复制后端文件"""
        logger.info("正在复制后端文件...")

        backend_files = []
        backend_dirs = ['src', 'ipc', 'launcher', 'updater']
        backend_files_list = ['main.py', 'start_fastblog.py', 'requirements.txt',
                              'version.txt', '.env_example']

        # 复制目录
        for dir_name in backend_dirs:
            src_dir = self.project_root / dir_name
            if src_dir.exists():
                dst_dir = self.release_dir / dir_name
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                # 收集所有文件
                for root, dirs, files in os.walk(dst_dir):
                    for file in files:
                        backend_files.append(Path(root) / file)
                logger.info(f"已复制目录: {dir_name}")

        # 复制单独文件
        for file_name in backend_files_list:
            src_file = self.project_root / file_name
            if src_file.exists():
                dst_file = self.release_dir / file_name
                shutil.copy2(src_file, dst_file)
                backend_files.append(dst_file)
                logger.info(f"已复制文件: {file_name}")

        return backend_files

    def build_frontend(self) -> List[Path]:
        """构建前端应用"""
        logger.info("正在构建前端应用...")

        frontend_files = []
        frontend_dir = self.project_root / "frontend-next"

        if not frontend_dir.exists():
            logger.warning("前端目录不存在，跳过前端构建")
            return frontend_files

        try:
            # 构建Next.js应用
            build_cmd = ["npm", "run", "build"]
            result = subprocess.run(
                build_cmd,
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                logger.error(f"前端构建失败: {result.stderr}")
                raise Exception("前端构建失败")

            logger.info("前端构建完成")

            # 复制构建产物
            next_dir = frontend_dir / ".next"
            if next_dir.exists():
                dst_next_dir = self.release_dir / "frontend-next" / ".next"
                shutil.copytree(next_dir, dst_next_dir, dirs_exist_ok=True)
                # 收集构建文件
                for root, dirs, files in os.walk(dst_next_dir):
                    for file in files:
                        frontend_files.append(Path(root) / file)

            # 复制其他必要文件
            frontend_files_needed = [
                'package.json', 'next.config.ts', 'tsconfig.json',
                '.env_example', '.gitignore'
            ]

            for file_name in frontend_files_needed:
                src_file = frontend_dir / file_name
                if src_file.exists():
                    dst_file = self.release_dir / "frontend-next" / file_name
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    frontend_files.append(dst_file)

            logger.info(f"已复制 {len(frontend_files)} 个前端文件")

        except subprocess.TimeoutExpired:
            logger.error("前端构建超时")
            raise Exception("前端构建超时")
        except Exception as e:
            logger.error(f"前端构建异常: {e}")
            raise

        return frontend_files

    def copy_static_assets(self) -> List[Path]:
        """复制静态资源"""
        logger.info("正在复制静态资源...")

        static_files = []
        static_dir = self.project_root / "static"

        if static_dir.exists():
            dst_static_dir = self.release_dir / "static"
            shutil.copytree(static_dir, dst_static_dir, dirs_exist_ok=True)

            # 收集静态文件
            for root, dirs, files in os.walk(dst_static_dir):
                for file in files:
                    static_files.append(Path(root) / file)

            logger.info(f"已复制 {len(static_files)} 个静态文件")

        return static_files

    def create_startup_scripts(self) -> List[Path]:
        """创建启动脚本"""
        logger.info("正在创建启动脚本...")

        scripts = []

        # Windows批处理脚本
        win_script = self.release_dir / "start_fastblog.bat"
        win_script_content = f"""@echo off
REM FastBlog {self.version} 启动脚本 (Windows)
cd /d "%~dp0"
python start_fastblog.py
pause
"""
        with open(win_script, 'w', encoding='utf-8') as f:
            f.write(win_script_content)
        scripts.append(win_script)

        # Linux/Mac Shell脚本
        unix_script = self.release_dir / "start_fastblog.sh"
        unix_script_content = f"""#!/bin/bash
# FastBlog {self.version} 启动脚本 (Linux/macOS)
cd "$(dirname "$0")"
python3 start_fastblog.py
"""
        with open(unix_script, 'w', encoding='utf-8') as f:
            f.write(unix_script_content)
        os.chmod(unix_script, 0o755)  # 设置执行权限
        scripts.append(unix_script)

        # README文件
        readme_file = self.release_dir / "README.md"
        readme_content = f"""# FastBlog v{self.version}

## 简介
FastBlog 是一个现代化的博客系统，基于FastAPI和Next.js构建。

## 系统要求
- Python 3.8+
- Node.js 18+ (如果需要重新构建前端)
- 数据库支持: PostgreSQL, MySQL, SQLite

## 安装步骤

### 1. 安装Python依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境
复制 `.env_example` 为 `.env` 并根据需要修改配置：
```bash
cp .env_example .env
```

### 3. 启动应用
Windows:
```cmd
start_fastblog.bat
```

Linux/macOS:
```bash
./start_fastblog.sh
```

或者直接运行：
```bash
python start_fastblog.py
```

## 目录结构
- `src/` - 后端源代码
- `frontend-next/` - 前端源代码
- `launcher/` - 应用启动器
- `updater/` - 自动更新系统
- `static/` - 静态资源文件

## 访问地址
默认情况下，应用将在以下地址运行：
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs

## 更多信息
请访问项目文档获取详细信息。
"""
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        scripts.append(readme_file)

        logger.info(f"已创建 {len(scripts)} 个启动脚本和文档")
        return scripts

    def create_checksums(self, all_files: List[Path]) -> Path:
        """创建校验和文件"""
        logger.info("正在创建校验和文件...")

        checksums = {}
        for file_path in all_files:
            try:
                rel_path = file_path.relative_to(self.release_dir)
                file_hash = self.get_file_hash(file_path)
                checksums[str(rel_path).replace('\\', '/')] = file_hash
            except Exception as e:
                logger.warning(f"计算文件哈希失败 {file_path}: {e}")

        # 写入JSON格式的校验和文件
        checksum_file = self.release_dir / "CHECKSUMS.json"
        with open(checksum_file, 'w', encoding='utf-8') as f:
            json.dump(checksums, f, indent=2, ensure_ascii=False)

        # 写入传统格式的校验和文件
        checksum_txt = self.release_dir / "CHECKSUMS.txt"
        with open(checksum_txt, 'w', encoding='utf-8') as f:
            for file_path, file_hash in checksums.items():
                f.write(f"{file_hash}  {file_path}\n")

        logger.info(f"校验和文件已创建: {checksum_file}")
        return checksum_file

    def parse_commit_message(self, subject: str) -> Optional[Dict]:
        """解析约定式提交的消息，返回类型、作用域、是否破坏性变更和主题"""
        pattern = r'^(?P<type>\w+)(?:\((?P<scope>[\w-]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$'
        match = re.match(pattern, subject)
        if match:
            return {
                'type': match.group('type'),
                'scope': match.group('scope'),
                'breaking': bool(match.group('breaking')),
                'subject': match.group('subject').strip()
            }
        return None

    def get_commits_since_last_tag(self) -> List[Dict]:
        """获取从上一个标签到当前版本标签之间的提交信息（支持 v 和 V 前缀）"""
        commits = []
        try:
            # 检查是否在 Git 仓库中
            subprocess.run(["git", "rev-parse", "--git-dir"], check=True,
                           capture_output=True, encoding='utf-8')

            # 尝试两种前缀，找到实际存在的标签
            possible_tags = [f"v{self.version}", f"V{self.version}"]
            current_tag = None
            for tag in possible_tags:
                try:
                    subprocess.run(["git", "rev-parse", tag], check=True,
                                   capture_output=True, encoding='utf-8')
                    current_tag = tag
                    break
                except subprocess.CalledProcessError:
                    continue

            if not current_tag:
                logger.warning(f"未找到与版本 {self.version} 匹配的标签（尝试了 {possible_tags}）")
                return commits

            # 获取上一个标签
            prev_tag = None
            try:
                result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0", f"{current_tag}^"],
                    check=True, capture_output=True, text=True, encoding='utf-8'
                )
                prev_tag = result.stdout.strip()
            except subprocess.CalledProcessError:
                # 没有上一个标签，则获取所有提交直到当前标签
                prev_tag = ""

            # 构建 commit 范围
            rev_range = f"{prev_tag}..{current_tag}" if prev_tag else current_tag

            # 获取每个 commit 的 hash、subject 和 body，用 --- 分隔
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H%n%s%n%b%n---", rev_range],
                check=True, capture_output=True, text=True, encoding='utf-8'
            )
            raw = result.stdout.strip()
            entries = raw.split("\n---\n")
            for entry in entries:
                if not entry.strip():
                    continue
                lines = entry.strip().split("\n")
                if len(lines) >= 3:
                    commit_hash = lines[0]
                    subject = lines[1]
                    body = "\n".join(lines[2:])
                    parsed = self.parse_commit_message(subject)
                    if parsed:
                        parsed['hash'] = commit_hash[:8]  # 短 hash
                        parsed['body'] = body.strip()
                        commits.append(parsed)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"无法获取 Git 提交信息: {e}")
        return commits

    def _format_commit_entry(self, commit: Dict) -> str:
        """格式化单个提交条目，包含可选的 body 详细信息"""
        scope = commit.get('scope')
        subject = commit['subject']
        hash_short = commit['hash']
        body = commit.get('body', '')

        # 构建主条目
        if scope:
            entry = f"- **{scope}**: {subject} ({hash_short})"
        else:
            entry = f"- {subject} ({hash_short})"

        # 如果有 body，将其拆分为多行并作为缩进的子列表添加
        if body:
            body_lines = [line.strip() for line in body.split('\n') if line.strip()]
            if body_lines:
                # 每个 body 行前加 4 个空格和一个短横，形成嵌套列表
                body_formatted = "\n".join([f"    - {line}" for line in body_lines])
                entry += f"\n{body_formatted}"

        return entry

    def create_release_notes(self) -> Path:
        """创建发布说明，自动填充从 commit 提取的内容（支持多行 body）"""
        logger.info("正在创建发布说明...")

        # 获取后端和前端版本信息
        backend_versions = get_backend_versions()
        frontend_versions = get_frontend_versions()

        # 获取提交信息并分类
        commits = self.get_commits_since_last_tag()
        features = []
        fixes = []
        docs = []
        perfs = []
        breaking_changes = []

        for c in commits:
            # 处理破坏性变更（无论类型，只要有 ! 标记）
            if c['breaking']:
                breaking_changes.append(self._format_commit_entry(c))
            # 按类型分类
            if c['type'] == 'feat':
                features.append(self._format_commit_entry(c))
            elif c['type'] == 'fix':
                fixes.append(self._format_commit_entry(c))
            elif c['type'] == 'docs':
                docs.append(self._format_commit_entry(c))
            elif c['type'] == 'perf':
                perfs.append(self._format_commit_entry(c))
            # 其他类型可忽略或按需添加

        # 若无对应提交，使用占位符
        if not features:
            features = ["- [在此处添加新功能描述]"]
        if not fixes:
            fixes = ["- [在此处添加修复的问题]"]
        if not perfs:
            perfs = ["- [在此处添加性能改进]"]
        if not docs:
            docs = []  # 文档更新可选，不强制显示
        if not breaking_changes:
            breaking_changes = ["- 无破坏性变更"]

        # 构建各部分内容
        features_section = "\n".join(features)
        fixes_section = "\n".join(fixes)
        perfs_section = "\n".join(perfs)
        docs_section = "\n".join(docs) if docs else "无"
        breaking_section = "\n".join(breaking_changes)

        release_notes = self.release_dir / "RELEASE_NOTES.md"
        notes_content = f"""# FastBlog v{self.version} 发布说明

## 🎉 新特性

### 核心功能
{features_section}

### 性能优化
{perfs_section}

### 文档更新
{docs_section}

## 🐛 问题修复

{fixes_section}

## ⚠️ 破坏性变更

{breaking_section}

## 🔧 工作流配置

### 后端更新
{format_version_list(backend_versions)}

### 前端更新
{format_version_list(frontend_versions)}

## 📦 安装说明

请参考 README.md 文件获取详细的安装和配置说明。

## 🙏 致谢

感谢所有为此版本做出贡献的开发者！

---
发布日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        with open(release_notes, 'w', encoding='utf-8') as f:
            f.write(notes_content)
        logger.info(f"发布说明已创建: {release_notes}")
        return release_notes

    def build(self) -> Dict[str, any]:
        """执行完整构建流程"""
        logger.info("=== 开始构建发布版本 ===")
        start_time = time.time()

        try:
            # 1. 复制后端文件
            backend_files = self.copy_backend_files()

            # 2. 构建前端
            frontend_files = self.build_frontend()

            # 3. 复制静态资源
            static_files = self.copy_static_assets()

            # 4. 创建启动脚本
            script_files = self.create_startup_scripts()

            # 5. 收集所有文件
            all_files = backend_files + frontend_files + static_files + script_files

            # 6. 创建校验和
            checksum_file = self.create_checksums(all_files)
            all_files.append(checksum_file)

            # 7. 创建发布说明
            release_notes = self.create_release_notes()
            all_files.append(release_notes)

            # 8. 创建ZIP包
            zip_file = self.create_zip_package()

            # 9. 创建额外的校验和文件（针对ZIP包）
            zip_checksum_file = self.output_dir / f"fastblog-v{self.version}-checksums.txt"
            zip_hash = self.get_file_hash(zip_file)
            with open(zip_checksum_file, 'w', encoding='utf-8') as f:
                f.write(f"{zip_hash}  fastblog-v{self.version}.zip\n")

            build_time = time.time() - start_time

            result = {
                'success': True,
                'version': self.version,
                'files_count': len(all_files),
                'zip_file': str(zip_file),
                'zip_size_mb': round(zip_file.stat().st_size / (1024 * 1024), 2),
                'build_time_seconds': round(build_time, 2),
                'release_dir': str(self.release_dir)
            }

            logger.info("=== 构建完成 ===")
            logger.info(f"版本: {result['version']}")
            logger.info(f"文件数量: {result['files_count']}")
            logger.info(f"ZIP包大小: {result['zip_size_mb']} MB")
            logger.info(f"构建耗时: {result['build_time_seconds']} 秒")

            return result

        except Exception as e:
            logger.error(f"构建失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(self.build_temp, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")

    def create_zip_package(self) -> Path:
        """创建ZIP压缩包"""
        logger.info("正在创建ZIP压缩包...")

        zip_filename = self.output_dir / f"fastblog-v{self.version}.zip"

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.release_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_name = file_path.relative_to(self.output_dir)
                    zipf.write(file_path, arc_name)

        logger.info(f"ZIP包已创建: {zip_filename}")
        return zip_filename


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='FastBlog 发布构建工具')
    parser.add_argument('--version', '-v', required=True, help='版本号')
    parser.add_argument('--output', '-o', default='release', help='输出目录')
    parser.add_argument('--verbose', action='store_true', help='详细输出')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    builder = ReleaseBuilder(args.version, args.output)
    result = builder.build()

    if result['success']:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)
    else:
        print(f"构建失败: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()