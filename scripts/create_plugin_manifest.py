#!/usr/bin/env python3
"""
插件清单生成器

用于快速创建符合规范的插件 metadata.json 文件

用法:
    python scripts/create_plugin_manifest.py --name "My Plugin" --output plugins/my-plugin
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.services.plugin_manifest import ManifestValidator


def main():
    parser = argparse.ArgumentParser(
        description='创建标准化的插件清单文件 (metadata.json)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python create_plugin_manifest.py --name "SEO Optimizer"
  
  # 指定输出目录
  python create_plugin_manifest.py --name "My Plugin" --output plugins/my-plugin
  
  # 带作者信息
  python create_plugin_manifest.py --name "Analytics" --author "John Doe" --email "john@example.com"
  
  # 声明权限
  python create_plugin_manifest.py --name "Email Plugin" --capabilities read:articles send:email
        """
    )

    parser.add_argument('--name', '-n', required=True, help='插件名称')
    parser.add_argument('--output', '-o', default=None, help='输出目录（默认: plugins/<slug>）')
    parser.add_argument('--version', '-v', default='1.0.0', help='版本号（默认: 1.0.0）')
    parser.add_argument('--description', '-d', default='', help='插件描述')
    parser.add_argument('--author', '-a', default='Your Name', help='作者名称')
    parser.add_argument('--email', '-e', default='', help='作者邮箱')
    parser.add_argument('--url', '-u', default='', help='作者网站')
    parser.add_argument('--license', '-l', default='MIT', help='许可证（默认: MIT）')
    parser.add_argument('--category', '-c', default='', help='分类')
    parser.add_argument('--capabilities', nargs='*', default=[],
                        help='权限声明列表，格式: resource:action')
    parser.add_argument('--hooks', nargs='*', default=[],
                        help='钩子列表')
    parser.add_argument('--dependencies', nargs='*', default=[],
                        help='Python依赖包列表')

    args = parser.parse_args()

    # 生成 slug
    slug = args.name.lower().replace(' ', '-').replace('_', '-')

    # 确定输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path('plugins') / slug

    # 创建目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 创建 manifest
    validator = ManifestValidator()
    manifest_file = validator.create_template(output_dir, args.name)

    print(f"✅ Manifest file created: {manifest_file}")
    print(f"\n📝 Next steps:")
    print(f"   1. Edit {manifest_file} to customize your plugin")
    print(f"   2. Create plugin.py in the same directory")
    print(f"   3. Test your plugin with: python main.py")
    print(f"\n📚 Documentation: https://athenavi.github.io/docs/plugins/development")

    return 0


if __name__ == '__main__':
    sys.exit(main())
