"""
Django 数据库初始化和创建管理员脚本
用于快速初始化 Django 数据库并创建默认超级管理员

使用方法:
    python scripts/quick_init.py

功能:
    - 运行数据库迁移
    - 创建或更新默认超级管理员账户
    - 显示登录信息
"""
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')

import django

# 防止重复初始化 Django
if not hasattr(django, '_setup_complete') or not django.apps.apps.ready:
    try:
        django.setup()
        django._setup_complete = True
    except RuntimeError as e:
        if "populate() isn't reentrant" in str(e):
            pass  # Django 已经初始化过了
        else:
            raise

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone


def main():
    print("=" * 60)
    print("Django 数据库初始化")
    print("=" * 60)

    # Step 1: 运行迁移（忽略 system check）
    print("\n[1/2] 运行数据库迁移...")
    try:
        call_command('migrate', '--run-syncdb', verbosity=1, skip_checks=True)
        print("✓ 数据库迁移完成")
    except Exception as e:
        print(f"迁移过程有警告：{e}")

    # Step 2: 创建超级管理员
    print("\n[2/2] 创建超级管理员账户...")
    User = get_user_model()

    admin_username = 'admin'
    admin_email = 'admin@example.com'
    # 生成随机强密码（仅在非交互式环境下使用）
    import secrets
    import string
    admin_password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(16))

    try:
        if User.objects.filter(username=admin_username).exists():
            print(f"⚠ 用户 '{admin_username}' 已存在，更新密码...")
            admin = User.objects.get(username=admin_username)
            admin.password = make_password(admin_password)
            admin.is_staff = True
            admin.is_superuser = True
            admin.is_active = True
            admin.save()
            print("✓ 管理员密码已更新")
        else:
            # 直接创建用户并设置哈希密码
            admin = User(
                username=admin_username,
                email=admin_email,
                password=make_password(admin_password),
                is_staff=True,
                is_superuser=True,
                is_active=True,
                date_joined=str(timezone.now())
            )
            admin.save()
            print("✓ 管理员账户创建成功")

        print("\n" + "=" * 60)
        print("超级管理员登录信息：")
        print("=" * 60)
        print(f"用户名：{admin_username}")
        print(f"邮箱：{admin_email}")
        print(f"密码：{admin_password}")
        print("=" * 60)
        print("⚠️  重要提示：")
        print("1. 请立即登录系统修改密码")
        print("2. 此密码已记录在上方，请妥善保存")
        print("3. 生产环境请使用环境变量设置管理员密码")
        print("=" * 60)
        print("\n现在可以启动服务器并登录系统！")

    except Exception as e:
        print(f"❌ 创建管理员失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
