"""
404 Monitor 插件数据库初始化
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.plugin_database import plugin_db


def init_404_monitor_db():
    """
    初始化 404 Monitor 插件数据库
    
    创建必要的表结构用于持久化存储 404 记录
    """
    slug = "404-monitor"

    # 检查表是否已存在
    if not plugin_db.table_exists(slug, "forty_four_records"):
        # 创建 404 记录表
        plugin_db.execute_update(slug, """
                                       CREATE TABLE IF NOT EXISTS forty_four_records
                                       (
                                           id             INTEGER PRIMARY KEY AUTOINCREMENT,
                                           url            TEXT NOT NULL,
                                           ip             TEXT,
                                           referrer       TEXT,
                                           user_agent     TEXT,
                                           method         TEXT      DEFAULT 'GET',
                                           timestamp      TEXT NOT NULL,
                                           timestamp_unix REAL NOT NULL,
                                           created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                       )
                                       """)

        # 创建索引以提高查询性能
        plugin_db.execute_update(slug,
                                 "CREATE INDEX IF NOT EXISTS idx_url ON forty_four_records(url)")
        plugin_db.execute_update(slug,
                                 "CREATE INDEX IF NOT EXISTS idx_timestamp ON forty_four_records(timestamp_unix)")
        plugin_db.execute_update(slug,
                                 "CREATE INDEX IF NOT EXISTS idx_ip ON forty_four_records(ip)")

        print("[PluginDB] 404 Monitor database initialized")
    else:
        print("[PluginDB] 404 Monitor database already exists")


if __name__ == "__main__":
    init_404_monitor_db()
