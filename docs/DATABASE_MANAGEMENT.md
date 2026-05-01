# 数据库管理工具使用指南

FastBlog 提供了完整的数据库管理工具，支持备份、恢复、清理等功能。

## 快速开始

### 1. 安装依赖

```bash
pip install python-dotenv
```

确保系统已安装 PostgreSQL 客户端工具：

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# macOS
brew install postgresql

# Windows
# 下载并安装 PostgreSQL: https://www.postgresql.org/download/windows/
```

### 2. 配置数据库

确保 `.env` 文件中配置了正确的数据库信息：

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=fast_blog
```

---

## 命令说明

### 1. 备份数据库

**基本用法：**

```bash
python scripts/db_manager.py backup
```

**指定输出文件名：**

```bash
python scripts/db_manager.py backup -o my_backup.sql
```

**输出示例：**

```
📦 开始备份数据库...
   目标文件: backups/database/backup_20260501_143022.sql
✅ 备份完成!
   文件大小: 15.23 MB
   保存位置: backups/database/backup_20260501_143022.sql
```

**特性：**

- ✅ 自动压缩（使用 PostgreSQL 自定义格式）
- ✅ 时间戳命名
- ✅ 保存到 `backups/database/` 目录
- ✅ 显示文件大小

---

### 2. 恢复数据库

**基本用法：**

```bash
python scripts/db_manager.py restore backups/database/backup_20260501_143022.sql
```

**输出示例：**

```
🔄 开始恢复数据库...
   备份文件: backups/database/backup_20260501_143022.sql
   ⚠️  警告: 这将覆盖当前数据库!
   确认继续? (yes/no): yes
   正在恢复...
✅ 数据库恢复完成!
```

**⚠️ 重要提示：**

- 恢复操作会**覆盖**当前数据库
- 需要输入 `yes` 确认
- 建议先备份当前数据

---

### 3. 列出备份

**基本用法：**

```bash
python scripts/db_manager.py list
```

**输出示例：**

```
文件名                                      大小(MB)     创建时间
--------------------------------------------------------------------------------
backup_20260501_100000.sql                 12.45        2026-05-01 10:00:00
backup_20260501_120000.sql                 13.67        2026-05-01 12:00:00
backup_20260501_143022.sql                 15.23        2026-05-01 14:30:22

总计: 3 个备份
```

---

### 4. 清理旧备份

**基本用法（保留最近 5 个）：**

```bash
python scripts/db_manager.py cleanup
```

**指定保留数量：**

```bash
python scripts/db_manager.py cleanup -n 10
```

**输出示例：**

```
   🗑️  删除: backup_20260428_100000.sql
   🗑️  删除: backup_20260429_100000.sql
✅ 清理完成，删除了 2 个旧备份
```

**建议：**

- 开发环境：保留 3-5 个
- 生产环境：保留 7-10 个
- 定期清理以节省磁盘空间

---

### 5. 查看状态

**基本用法：**

```bash
python scripts/db_manager.py status
```

**输出示例：**

```
============================================================
数据库状态
============================================================

📊 连接信息:
   主机: localhost
   端口: 5432
   数据库: fast_blog
   用户: postgres

💾 备份统计:
   备份数量: 5
   总大小: 67.89 MB
   最新备份: backup_20260501_143022.sql
   创建时间: 2026-05-01 14:30:22
============================================================
```

---

## 自动化备份

### 1. Cron 定时任务（Linux/Mac）

**每天凌晨 2 点备份：**

```bash
# 编辑 crontab
crontab -e

# 添加以下行
0 2 * * * cd /path/to/fast_blog && python scripts/db_manager.py backup >> logs/db_backup.log 2>&1
```

**每周日清理旧备份：**

```bash
0 3 * * 0 cd /path/to/fast_blog && python scripts/db_manager.py cleanup -n 7 >> logs/db_cleanup.log 2>&1
```

### 2. Task Scheduler（Windows）

**创建批处理文件 `backup.bat`：**

```batch
@echo off
cd C:\path\to\fast_blog
python scripts\db_manager.py backup >> logs\db_backup.log 2>&1
```

**设置定时任务：**

1. 打开任务计划程序
2. 创建基本任务
3. 选择触发器（每天）
4. 选择操作（启动程序）
5. 浏览到 `backup.bat`

### 3. Systemd Timer（Linux）

**创建服务文件 `/etc/systemd/system/fastblog-backup.service`：**

```ini
[Unit]
Description = FastBlog Database Backup
After = network.target

[Service]
Type = oneshot
User = www-data
WorkingDirectory = /path/to/fast_blog
ExecStart = /usr/bin/python3 scripts/db_manager.py backup

[Install]
WantedBy = multi-user.target
```

**创建定时器 `/etc/systemd/system/fastblog-backup.timer`：**

```ini
[Unit]
Description = Run FastBlog Backup Daily

[Timer]
OnCalendar = *-*-* 02:00:00
Persistent = true

[Install]
WantedBy = timers.target
```

**启用定时器：**

```bash
sudo systemctl enable fastblog-backup.timer
sudo systemctl start fastblog-backup.timer
```

---

## 最佳实践

### 1. 备份策略

**推荐方案：**

| 频率  | 保留数量 | 说明        |
|-----|------|-----------|
| 每小时 | 24 个 | 高频率备份（可选） |
| 每天  | 7 个  | 每日备份      |
| 每周  | 4 个  | 每周备份      |
| 每月  | 12 个 | 月度归档      |

**实现示例：**

```bash
# 每天备份
0 2 * * * python scripts/db_manager.py backup

# 每周日清理，保留 7 天
0 3 * * 0 python scripts/db_manager.py cleanup -n 7

# 每月 1 号归档
0 4 1 * * cp backups/database/backup_*.sql backups/archive/
```

### 2. 异地备份

**同步到远程服务器：**

```bash
# 使用 rsync
rsync -avz backups/database/ user@remote-server:/backup/fastblog/

# 使用 scp
scp backups/database/backup_*.sql user@remote-server:/backup/fastblog/
```

**同步到云存储（AWS S3）：**

```bash
# 安装 AWS CLI
pip install awscli

# 同步备份
aws s3 sync backups/database/ s3://your-bucket/fastblog-backups/
```

**同步到 Google Drive：**

```bash
# 使用 rclone
rclone copy backups/database/ gdrive:fastblog-backups/
```

### 3. 备份验证

**定期检查备份完整性：**

```bash
#!/bin/bash
# verify_backup.sh

LATEST_BACKUP=$(ls -t backups/database/backup_*.sql | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 没有找到备份文件"
    exit 1
fi

echo "验证备份: $LATEST_BACKUP"

# 测试恢复（到临时数据库）
pg_restore --list "$LATEST_BACKUP" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 备份文件完整"
else
    echo "❌ 备份文件损坏"
    exit 1
fi
```

### 4. 监控和告警

**监控备份状态：**

```python
import os
from datetime import datetime, timedelta


def check_backup_status():
    """检查备份是否正常"""
    backup_dir = "backups/database"

    # 获取最新备份
    backups = sorted(os.listdir(backup_dir))
    if not backups:
        send_alert("没有备份文件!")
        return

    latest = backups[-1]
    backup_time = datetime.strptime(latest.split('_')[1].split('.')[0], "%Y%m%d%H%M%S")

    # 检查备份是否超过 24 小时
    if datetime.now() - backup_time > timedelta(hours=24):
        send_alert(f"备份过期! 最新备份: {latest}")
    else:
        print("✅ 备份正常")


def send_alert(message):
    """发送告警（邮件/Slack/钉钉等）"""
    # 实现告警逻辑
    pass
```

---

## 故障排查

### 问题 1: pg_dump 命令未找到

**症状：**

```
❌ 错误: 未找到 pg_dump 命令
```

**解决：**

```bash
# 检查 PostgreSQL 客户端是否安装
which pg_dump

# 安装 PostgreSQL 客户端
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# macOS
brew install postgresql
```

### 问题 2: 认证失败

**症状：**

```
pg_dump: error: connection to server failed: FATAL: password authentication failed
```

**解决：**

1. 检查 `.env` 中的密码是否正确
2. 测试手动连接：
   ```bash
   psql -h localhost -U postgres -d fast_blog
   ```
3. 检查 `pg_hba.conf` 配置

### 问题 3: 权限不足

**症状：**

```
pg_dump: error: permission denied for database
```

**解决：**

```sql
-- 授予用户权限
GRANT
CONNECT
ON DATABASE fast_blog TO your_user;
GRANT USAGE ON SCHEMA
public TO your_user;
GRANT
SELECT
ON ALL TABLES IN SCHEMA public TO your_user;
```

### 问题 4: 磁盘空间不足

**症状：**

```
No space left on device
```

**解决：**

```bash
# 检查磁盘空间
df -h

# 清理旧备份
python scripts/db_manager.py cleanup -n 3

# 压缩备份文件
gzip backups/database/old_backup.sql
```

---

## 高级用法

### 1. 选择性备份

**只备份特定表：**

```bash
pg_dump -h localhost -U postgres -d fast_blog \
  -t articles -t categories \
  -F c -f selective_backup.sql
```

**排除大表：**

```bash
pg_dump -h localhost -U postgres -d fast_blog \
  -T logs -T sessions \
  -F c -f backup_without_logs.sql
```

### 2. 增量备份

PostgreSQL 支持 WAL 日志实现增量备份：

```bash
# 启用 WAL 归档
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /path/to/archive/%f'

# 基础备份
pg_basebackup -D /path/to/basebackup -Ft -z -P
```

### 3. 点对点恢复（PITR）

恢复到特定时间点：

```bash
# 1. 恢复基础备份
pg_restore -d fast_blog base_backup.sql

# 2. 应用 WAL 日志到指定时间
# recovery.conf
restore_command = 'cp /path/to/archive/%f %p'
recovery_target_time = '2026-05-01 14:30:00'
```

---

## 相关资源

- [PostgreSQL 备份文档](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump 手册](https://www.postgresql.org/docs/current/app-pgdump.html)
- [pg_restore 手册](https://www.postgresql.org/docs/current/app-pgrestore.html)
- [配置指南](./CONFIGURATION_GUIDE.md)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01

