#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理工具

提供数据库备份、恢复、迁移等功能
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_config: dict):
        """
        初始化数据库管理器
        
        Args:
            db_config: 数据库配置字典
        """
        self.db_config = db_config
        self.backup_dir = Path("backups/database")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, output_file: Optional[str] = None) -> str:
        """
        备份数据库
        
        Args:
            output_file: 输出文件名（可选）
            
        Returns:
            备份文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"backup_{timestamp}.sql"

        backup_path = self.backup_dir / output_file

        print(f"📦 开始备份数据库...")
        print(f"   目标文件: {backup_path}")

        try:
            # 构建 pg_dump 命令
            cmd = [
                "pg_dump",
                "-h", self.db_config.get("DB_HOST", "localhost"),
                "-p", str(self.db_config.get("DB_PORT", 5432)),
                "-U", self.db_config.get("DB_USER", "postgres"),
                "-d", self.db_config.get("DB_NAME", "fast_blog"),
                "-F", "c",  # 自定义格式（压缩）
                "-f", str(backup_path)
            ]

            # 设置环境变量（密码）
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config.get("DB_PASSWORD", "")

            # 执行备份
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            # 获取文件大小
            file_size = backup_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            print(f"✅ 备份完成!")
            print(f"   文件大小: {file_size_mb:.2f} MB")
            print(f"   保存位置: {backup_path}")

            return str(backup_path)

        except FileNotFoundError:
            print("❌ 错误: 未找到 pg_dump 命令")
            print("   请确保 PostgreSQL 客户端工具已安装")
            raise
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            raise

    def restore(self, backup_file: str) -> bool:
        """
        恢复数据库
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            是否成功
        """
        backup_path = Path(backup_file)

        if not backup_path.exists():
            print(f"❌ 错误: 备份文件不存在: {backup_file}")
            return False

        print(f"🔄 开始恢复数据库...")
        print(f"   备份文件: {backup_path}")
        print(f"   ⚠️  警告: 这将覆盖当前数据库!")

        confirm = input("   确认继续? (yes/no): ")
        if confirm.lower() != "yes":
            print("   操作已取消")
            return False

        try:
            # 构建 pg_restore 命令
            cmd = [
                "pg_restore",
                "-h", self.db_config.get("DB_HOST", "localhost"),
                "-p", str(self.db_config.get("DB_PORT", 5432)),
                "-U", self.db_config.get("DB_USER", "postgres"),
                "-d", self.db_config.get("DB_NAME", "fast_blog"),
                "--clean",  # 清理现有对象
                "--if-exists",
                "--no-owner",
                str(backup_path)
            ]

            # 设置环境变量（密码）
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config.get("DB_PASSWORD", "")

            # 执行恢复
            print("   正在恢复...")
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise Exception(f"pg_restore failed: {result.stderr}")

            print("✅ 数据库恢复完成!")
            return True

        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            return False

    def list_backups(self) -> list:
        """
        列出所有备份文件
        
        Returns:
            备份文件列表
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob("backup_*.sql")):
            stat = backup_file.stat()
            size_mb = stat.st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(stat.st_mtime)

            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size_mb": round(size_mb, 2),
                "created_at": modified.strftime("%Y-%m-%d %H:%M:%S")
            })

        return backups

    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """
        清理旧备份文件
        
        Args:
            keep_count: 保留的备份数量
            
        Returns:
            删除的文件数量
        """
        backups = self.list_backups()

        if len(backups) <= keep_count:
            print(f"ℹ️  当前有 {len(backups)} 个备份，无需清理")
            return 0

        # 按时间排序，删除最旧的
        backups_to_delete = backups[:-keep_count]
        deleted_count = 0

        for backup in backups_to_delete:
            try:
                Path(backup["path"]).unlink()
                print(f"   🗑️  删除: {backup['filename']}")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ 删除失败: {backup['filename']} - {e}")

        print(f"✅ 清理完成，删除了 {deleted_count} 个旧备份")
        return deleted_count

    def show_status(self):
        """显示数据库状态"""
        print("=" * 60)
        print("数据库状态")
        print("=" * 60)

        # 数据库连接信息
        print(f"\n📊 连接信息:")
        print(f"   主机: {self.db_config.get('DB_HOST', 'localhost')}")
        print(f"   端口: {self.db_config.get('DB_PORT', 5432)}")
        print(f"   数据库: {self.db_config.get('DB_NAME', 'fast_blog')}")
        print(f"   用户: {self.db_config.get('DB_USER', 'postgres')}")

        # 备份统计
        backups = self.list_backups()
        total_size = sum(b["size_mb"] for b in backups)

        print(f"\n💾 备份统计:")
        print(f"   备份数量: {len(backups)}")
        print(f"   总大小: {total_size:.2f} MB")

        if backups:
            latest = backups[-1]
            print(f"   最新备份: {latest['filename']}")
            print(f"   创建时间: {latest['created_at']}")

        print("=" * 60)


def load_db_config() -> dict:
    """从 .env 文件加载数据库配置"""
    from dotenv import load_dotenv

    # 加载 .env 文件
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    config = {
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": int(os.getenv("DB_PORT", "5432")),
        "DB_USER": os.getenv("DB_USER", "postgres"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
        "DB_NAME": os.getenv("DB_NAME", "fast_blog"),
    }

    return config


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="FastBlog 数据库管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # backup 命令
    backup_parser = subparsers.add_parser("backup", help="备份数据库")
    backup_parser.add_argument("-o", "--output", help="输出文件名")

    # restore 命令
    restore_parser = subparsers.add_parser("restore", help="恢复数据库")
    restore_parser.add_argument("file", help="备份文件路径")

    # list 命令
    subparsers.add_parser("list", help="列出所有备份")

    # cleanup 命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理旧备份")
    cleanup_parser.add_argument("-n", "--keep", type=int, default=5,
                                help="保留的备份数量（默认: 5）")

    # status 命令
    subparsers.add_parser("status", help="显示数据库状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 加载配置
    db_config = load_db_config()
    db_manager = DatabaseManager(db_config)

    # 执行命令
    try:
        if args.command == "backup":
            db_manager.backup(args.output)

        elif args.command == "restore":
            success = db_manager.restore(args.file)
            if not success:
                sys.exit(1)

        elif args.command == "list":
            backups = db_manager.list_backups()

            if not backups:
                print("没有找到备份文件")
                return

            print(f"\n{'文件名':<40} {'大小(MB)':<12} {'创建时间'}")
            print("-" * 80)

            for backup in backups:
                print(f"{backup['filename']:<40} {backup['size_mb']:<12.2f} {backup['created_at']}")

            print(f"\n总计: {len(backups)} 个备份")

        elif args.command == "cleanup":
            db_manager.cleanup_old_backups(args.keep)

        elif args.command == "status":
            db_manager.show_status()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
