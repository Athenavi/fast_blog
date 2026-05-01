# 系统监控工具使用指南

FastBlog 提供了完整的系统监控工具，实时监控服务器资源使用情况并发送告警。

## 快速开始

### 1. 安装依赖

```bash
pip install psutil requests
```

### 2. 查看系统状态

```bash
python scripts/system_monitor.py status
```

**输出示例：**

```
======================================================================
系统监控状态
======================================================================

🟢 CPU 使用率: 25.3%
   核心数: 4

🟢 内存使用: 45.2%
   已用: 3.62 GB / 8.00 GB

🟡 磁盘使用: 72.8%
   已用: 36.40 GB / 50.00 GB

🟢 系统负载:
   1分钟: 0.85
   5分钟: 1.23
   15分钟: 1.45

📡 网络流量:
   发送: 125.67 MB
   接收: 456.89 MB

======================================================================
```

---

## 命令说明

### 1. 查看系统状态

**基本用法：**

```bash
python scripts/system_monitor.py status
```

**显示内容：**

- ✅ CPU 使用率和核心数
- ✅ 内存使用情况和总量
- ✅ 磁盘使用情况和总量
- ✅ 系统负载（1/5/15分钟）
- ✅ 网络流量统计

---

### 2. 持续监控

**基本用法（默认 60 秒间隔）：**

```bash
python scripts/system_monitor.py watch
```

**自定义检查间隔：**

```bash
python scripts/system_monitor.py watch -i 30
```

**输出示例：**

```
开始监控系统...
检查间隔: 30 秒
按 Ctrl+C 停止

🚨 告警: CPU 使用率过高: 85.2%
✅ 邮件告警已发送

🚨 告警: 内存使用率过高: 88.5%
✅ Webhook 告警已发送
```

**特性：**

- ✅ 实时监控
- ✅ 自动告警
- ✅ 冷却期机制（避免重复告警）
- ✅ 多通道通知

---

### 3. 配置监控阈值

**修改 CPU 阈值：**

```bash
python scripts/system_monitor.py config --cpu-threshold 90
```

**修改内存阈值：**

```bash
python scripts/system_monitor.py config --memory-threshold 90
```

**修改磁盘阈值：**

```bash
python scripts/system_monitor.py config --disk-threshold 95
```

**同时修改多个阈值：**

```bash
python scripts/system_monitor.py config \
  --cpu-threshold 85 \
  --memory-threshold 85 \
  --disk-threshold 90
```

---

## 配置文件

配置文件位置：`config/monitor.json`

### 默认配置

```json
{
  "thresholds": {
    "cpu_percent": 80,
    "memory_percent": 85,
    "disk_percent": 90,
    "load_average": 4.0
  },
  "alert_channels": {
    "email": {
      "enabled": false,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "",
      "password": "",
      "from_addr": "",
      "to_addrs": []
    },
    "webhook": {
      "enabled": false,
      "url": "",
      "method": "POST"
    }
  },
  "check_interval": 60,
  "cooldown_period": 300
}
```

### 配置项说明

#### 阈值配置 (thresholds)

| 参数             | 默认值 | 说明              |
|----------------|-----|-----------------|
| cpu_percent    | 80  | CPU 使用率告警阈值 (%) |
| memory_percent | 85  | 内存使用率告警阈值 (%)   |
| disk_percent   | 90  | 磁盘使用率告警阈值 (%)   |
| load_average   | 4.0 | 系统负载告警阈值        |

#### 邮件告警配置 (email)

```json
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "password": "your_app_password",
    "from_addr": "your_email@gmail.com",
    "to_addrs": ["admin@example.com", "devops@example.com"]
  }
}
```

**Gmail 设置步骤：**

1. 启用两步验证
2. 生成应用专用密码
3. 填入配置

#### Webhook 告警配置

**钉钉机器人：**

```json
{
  "webhook": {
    "enabled": true,
    "url": "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN",
    "method": "POST"
  }
}
```

**企业微信机器人：**

```json
{
  "webhook": {
    "enabled": true,
    "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY",
    "method": "POST"
  }
}
```

**Slack Webhook：**

```json
{
  "webhook": {
    "enabled": true,
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "method": "POST"
  }
}
```

#### 其他配置

| 参数              | 默认值 | 说明       |
|-----------------|-----|----------|
| check_interval  | 60  | 检查间隔（秒）  |
| cooldown_period | 300 | 告警冷却期（秒） |

---

## 告警级别

### 🟢 正常 (INFO)

- CPU < 70%
- 内存 < 70%
- 磁盘 < 70%
- 负载 < 2.0

### 🟡 警告 (WARNING)

- CPU 70-90%
- 内存 70-90%
- 磁盘 70-90%
- 负载 2.0-4.0

### 🔴 严重 (CRITICAL)

- CPU > 90%
- 内存 > 90%
- 磁盘 > 90%
- 负载 > 4.0

---

## 自动化部署

### 1. Systemd 服务（推荐）

创建服务文件 `/etc/systemd/system/fastblog-monitor.service`：

```ini
[Unit]
Description=FastBlog System Monitor
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/fastblog
ExecStart=/opt/fastblog/venv/bin/python scripts/system_monitor.py watch
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启用服务：**

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastblog-monitor
sudo systemctl start fastblog-monitor

# 查看状态
sudo systemctl status fastblog-monitor

# 查看日志
sudo journalctl -u fastblog-monitor -f
```

### 2. Cron 定时检查

**每 5 分钟检查一次：**

```bash
crontab -e

# 添加以下行
*/5 * * * * cd /opt/fastblog && python scripts/system_monitor.py status >> logs/monitor.log 2>&1
```

### 3. Docker 容器

**docker-compose.yml 中添加：**

```yaml
services:
  monitor:
    build: .
    command: python scripts/system_monitor.py watch
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
```

---

## 告警示例

### 邮件告警

**主题：** `[FastBlog Alert] WARNING: CPU`

**内容：**

```
告警类型: CPU
告警级别: WARNING
告警信息: CPU 使用率过高: 85.2%
当前值: 85.2
阈值: 80
时间: 2026-05-01 14:30:22
```

### 钉钉告警

```
🚨 FastBlog 告警
类型: CPU
级别: WARNING
信息: CPU 使用率过高: 85.2%
时间: 2026-05-01 14:30:22
```

### Slack 告警

类似钉钉，支持 Markdown 格式。

---

## 最佳实践

### 1. 阈值设置建议

**开发环境：**

```json
{
  "cpu_percent": 90,
  "memory_percent": 90,
  "disk_percent": 95,
  "load_average": 8.0
}
```

**生产环境：**

```json
{
  "cpu_percent": 75,
  "memory_percent": 80,
  "disk_percent": 85,
  "load_average": 3.0
}
```

**高可用环境：**

```json
{
  "cpu_percent": 60,
  "memory_percent": 70,
  "disk_percent": 75,
  "load_average": 2.0
}
```

### 2. 告警渠道选择

**单一项目：**

- 邮件告警即可

**团队协作：**

- 钉钉/企业微信群机器人
- Slack 频道

**关键业务：**

- 多渠道同时告警
- 电话/SMS 告警（需要额外集成）

### 3. 冷却期设置

**频繁告警场景：**

```json
{
  "cooldown_period": 600
}
```

**不敏感场景：**

```json
{
  "cooldown_period": 1800
}
```

### 4. 日志管理

**查看告警历史：**

```bash
cat logs/alerts.log
```

**清理旧日志：**

```bash
# 保留最近 30 天
find logs -name "alerts.log.*" -mtime +30 -delete
```

**日志轮转配置** `/etc/logrotate.d/fastblog-monitor`：

```
/opt/fastblog/logs/alerts.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 故障排查

### 问题 1: psutil 未安装

**症状：**

```
ModuleNotFoundError: No module named 'psutil'
```

**解决：**

```bash
pip install psutil
```

### 问题 2: 邮件发送失败

**症状：**

```
❌ 邮件发送失败: Connection refused
```

**解决：**

1. 检查 SMTP 服务器地址和端口
2. 验证用户名和密码
3. 检查防火墙设置
4. Gmail 需要使用应用专用密码

**测试连接：**

```python
import smtplib

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email@gmail.com', 'your_password')
print("Connection successful")
server.quit()
```

### 问题 3: Webhook 发送失败

**症状：**

```
❌ Webhook 发送失败: 403
```

**解决：**

1. 检查 Webhook URL 是否正确
2. 验证访问令牌是否有效
3. 检查机器人是否启用

**测试 Webhook：**

```bash
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'
```

### 问题 4: 权限不足

**症状：**

```
PermissionError: [Errno 13] Permission denied
```

**解决：**

```bash
# 修改文件所有者
sudo chown -R www-data:www-data /opt/fastblog/logs

# 或修改权限
chmod 644 logs/alerts.log
```

---

## 高级用法

### 1. 自定义告警规则

编辑 `scripts/system_monitor.py`，添加自定义检查：

```python
def check_custom_rules(self, metrics: dict) -> list:
    """自定义检查规则"""
    alerts = []
    
    # 检查特定进程
    for proc in psutil.process_iter(['name', 'cpu_percent']):
        if proc.info['name'] == 'python' and proc.info['cpu_percent'] > 50:
            alerts.append({
                "type": "PROCESS",
                "level": "WARNING",
                "message": f"Python 进程 CPU 使用率高: {proc.info['cpu_percent']}%"
            })
    
    return alerts
```

### 2. 集成 Prometheus

```python
from prometheus_client import Gauge, start_http_server

# 定义指标
CPU_GAUGE = Gauge('system_cpu_percent', 'CPU usage percent')
MEMORY_GAUGE = Gauge('system_memory_percent', 'Memory usage percent')

# 启动指标服务器
start_http_server(8000)

# 更新指标
CPU_GAUGE.set(metrics["cpu"]["percent"])
MEMORY_GAUGE.set(metrics["memory"]["percent"])
```

### 3. 生成监控报告

```python
def generate_daily_report(self):
    """生成每日监控报告"""
    import pandas as pd
    
    # 读取告警日志
    df = pd.read_csv('logs/alerts.log', names=['timestamp', 'level', 'message'])
    
    # 统计分析
    summary = df.groupby('level').size()
    
    # 生成报告
    report = f"""
# 每日监控报告

日期: {datetime.now().strftime('%Y-%m-%d')}

告警统计:
{summary.to_string()}

详细告警:
{df.tail(20).to_string()}
    """
    
    with open(f'reports/daily_{datetime.now().strftime("%Y%m%d")}.md', 'w') as f:
        f.write(report)
```

---

## 相关资源

- [psutil 文档](https://psutil.readthedocs.io/)
- [部署指南](./DEPLOYMENT_GUIDE.md)
- [日志系统](./LOGGING_SYSTEM.md)
- [数据库管理](./DATABASE_MANAGEMENT.md)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
