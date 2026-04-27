#!/usr/bin/env python3
"""
FastBlog CLI - 命令行工具

提供便捷的项目管理、代码生成、部署等功能

用法:
    fastblog <command> [options]

命令:
    create          创建新项目
    generate        生成代码(model, plugin, api)
    dev             启动开发服务器
    build           构建项目
    deploy          部署项目
    info            显示项目信息
    doctor          检查环境配置
"""

import argparse
import subprocess
import sys
from pathlib import Path


def cmd_create(args):
    """创建新项目"""
    project_name = args.name
    template = args.template or "default"

    print(f"🚀 Creating new FastBlog project: {project_name}")
    print(f"   Template: {template}")

    # 创建项目目录
    project_dir = Path(project_name)
    if project_dir.exists():
        print(f"❌ Error: Directory '{project_name}' already exists")
        sys.exit(1)

    project_dir.mkdir(parents=True)

    # 复制模板文件 (简化版:创建基本结构)
    print("📁 Creating project structure...")

    # 创建基本目录
    (project_dir / "apps").mkdir()
    (project_dir / "config").mkdir()
    (project_dir / "plugins").mkdir()
    (project_dir / "themes").mkdir()

    # 创建基本文件
    env_example = project_dir / ".env.example"
    env_example.write_text("""# FastBlog Environment Configuration
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/fastblog
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
""")

    readme = project_dir / "README.md"
    readme.write_text(f"""# {project_name}

A FastBlog powered blog site.

## Quick Start

1. Copy `.env.example` to `.env` and configure
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Start server: `python main.py`

## Development

```bash
# Start development server
fastblog dev

# Generate code
fastblog generate model Article
fastblog generate plugin my-plugin
```
""")

    print(f"✅ Project '{project_name}' created successfully!")
    print(f"\n📝 Next steps:")
    print(f"   cd {project_name}")
    print(f"   cp .env.example .env")
    print(f"   # Edit .env with your configuration")
    print(f"   fastblog dev")


def cmd_generate(args):
    """生成代码"""
    gen_type = args.type

    if gen_type == "model":
        generate_model(args)
    elif gen_type == "plugin":
        generate_plugin(args)
    elif gen_type == "api":
        generate_api(args)
    else:
        print(f"❌ Unknown generation type: {gen_type}")
        sys.exit(1)


def generate_model(args):
    """生成 Django/FastAPI 模型"""
    model_name = args.name
    app_name = args.app or "blog"

    print(f"🔧 Generating model: {model_name}")
    print(f"   App: {app_name}")

    # 这里可以添加实际的模型生成逻辑
    print(f"⚠️  Model generation not fully implemented yet")
    print(f"   Please manually create the model in apps/{app_name}/models.py")


def generate_plugin(args):
    """生成插件"""
    plugin_name = args.name
    output_dir = Path("plugins") / plugin_name.lower().replace(" ", "-")

    print(f"🔌 Generating plugin: {plugin_name}")
    print(f"   Output: {output_dir}")

    # 使用已有的 manifest 生成器
    from scripts.create_plugin_manifest import main as create_manifest
    sys.argv = [
        'create_plugin_manifest.py',
        '--name', plugin_name,
        '--output', str(output_dir)
    ]
    create_manifest()

    # 创建基本的 plugin.py
    plugin_file = output_dir / "plugin.py"
    if not plugin_file.exists():
        slug = plugin_name.lower().replace(" ", "-").replace("_", "-")
        plugin_code = f'''"""
{plugin_name} Plugin
"""

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class {plugin_name.replace(" ", "").replace("-", "")}Plugin(BasePlugin):
    """{plugin_name} Plugin"""
    
    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="{plugin_name}",
            slug="{slug}",
            version="1.0.0"
        )
    
    def register_hooks(self):
        """Register plugin hooks"""
        pass
    
    def activate(self):
        """Activate plugin"""
        super().activate()
        print(f"[{plugin_name}] Plugin activated")
    
    def deactivate(self):
        """Deactivate plugin"""
        super().deactivate()
        print(f"[{plugin_name}] Plugin deactivated")


# Plugin instance
plugin_instance = {plugin_name.replace(" ", "").replace("-", "")}Plugin()
'''
        plugin_file.write_text(plugin_code)
        print(f"✅ Created plugin.py")


def generate_api(args):
    """生成 API 端点"""
    endpoint_name = args.name

    print(f"🌐 Generating API endpoint: {endpoint_name}")
    print(f"⚠️  API generation not fully implemented yet")


def cmd_dev(args):
    """启动开发服务器"""
    print("🚀 Starting FastBlog development server...")

    # 设置环境变量
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')

    # 启动主应用
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host=args.host or "0.0.0.0",
            port=int(args.port) or 9421,
            reload=True,
            log_level="info"
        )
    except ImportError:
        print("❌ uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)


def cmd_build(args):
    """构建项目"""
    print("🔨 Building FastBlog...")

    # 前端构建
    frontend_dir = Path("frontend-next")
    if frontend_dir.exists():
        print("   Building frontend...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
            print("   ✅ Frontend built successfully")
        except subprocess.CalledProcessError:
            print("   ❌ Frontend build failed")
            sys.exit(1)
    else:
        print("   ⚠️  Frontend directory not found")

    print("✅ Build complete!")


def cmd_deploy(args):
    """部署项目"""
    print("🚀 Deploying FastBlog...")
    print("⚠️  Deployment not fully implemented yet")
    print("   Please use Docker or manual deployment for now")
    print("\n📚 Docker deployment:")
    print("   docker-compose up -d")


def cmd_info(args):
    """显示项目信息"""
    print("📊 FastBlog Project Information")
    print("=" * 50)

    # 版本信息
    version_file = Path("version.txt")
    if version_file.exists():
        version = version_file.read_text().strip()
        print(f"Version: {version}")

    # Python 版本
    print(f"Python: {sys.version.split()[0]}")

    # 项目路径
    print(f"Project Root: {Path.cwd()}")

    # 插件数量
    plugins_dir = Path("plugins")
    if plugins_dir.exists():
        plugin_count = len([p for p in plugins_dir.iterdir() if p.is_dir()])
        print(f"Plugins: {plugin_count}")

    # 主题数量
    themes_dir = Path("themes")
    if themes_dir.exists():
        theme_count = len([t for t in themes_dir.iterdir() if t.is_dir()])
        print(f"Themes: {theme_count}")


def cmd_doctor(args):
    """检查环境配置"""
    print("🔍 Checking environment...")
    print("=" * 50)

    issues = []

    # 检查 Python 版本
    if sys.version_info < (3, 8):
        issues.append("Python version should be >= 3.8")
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")

    # 检查 .env 文件
    env_file = Path(".env")
    if not env_file.exists():
        issues.append(".env file not found. Copy from .env.example")
    else:
        print("✅ .env file exists")

    # 检查依赖
    try:
        import fastapi
        print(f"✅ FastAPI {fastapi.__version__}")
    except ImportError:
        issues.append("FastAPI not installed")

    try:
        import django
        print(f"✅ Django {django.get_version()}")
    except ImportError:
        issues.append("Django not installed")

    # 检查数据库连接
    print("\n" + "=" * 50)
    if issues:
        print(f"❌ Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)
    else:
        print("✅ All checks passed!")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog='fastblog',
        description='FastBlog CLI - Command Line Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fastblog create my-blog
  fastblog generate plugin "SEO Optimizer"
  fastblog dev --port 8000
  fastblog doctor
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # create 命令
    create_parser = subparsers.add_parser('create', help='Create new project')
    create_parser.add_argument('name', help='Project name')
    create_parser.add_argument('--template', '-t', default='default', help='Template to use')

    # generate 命令
    gen_parser = subparsers.add_parser('generate', aliases=['gen'], help='Generate code')
    gen_parser.add_argument('type', choices=['model', 'plugin', 'api'], help='Type to generate')
    gen_parser.add_argument('name', help='Name')
    gen_parser.add_argument('--app', '-a', help='App name (for models)')

    # dev 命令
    dev_parser = subparsers.add_parser('dev', help='Start development server')
    dev_parser.add_argument('--host', default='0.0.0.0', help='Host')
    dev_parser.add_argument('--port', '-p', default='9421', help='Port')

    # build 命令
    subparsers.add_parser('build', help='Build project')

    # deploy 命令
    subparsers.add_parser('deploy', help='Deploy project')

    # info 命令
    subparsers.add_parser('info', help='Show project information')

    # doctor 命令
    subparsers.add_parser('doctor', help='Check environment')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 路由到对应的命令处理函数
    commands = {
        'create': cmd_create,
        'generate': cmd_generate,
        'gen': cmd_generate,
        'dev': cmd_dev,
        'build': cmd_build,
        'deploy': cmd_deploy,
        'info': cmd_info,
        'doctor': cmd_doctor,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
