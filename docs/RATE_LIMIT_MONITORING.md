# API 速率限制监控工具使用指南

FastBlog 提供了完整的 API 速率限制监控工具，帮助分析和优化 API 限流策略。

## 快速开始

### 1. 查看报告

```bash
python scripts/rate_limit_monitor.py report
```

**输出示例：**

```
================================================================================
API 速率限制监控报告
================================================================================

📊 总体统计:
   总请求数: 15,234
   允许请求: 14,890 (97.74%)
   阻止请求: 344 (2.26%)

🔗 热门 API 端点 (Top 10):
   /api/v1/articles                         5,678 ██████████████████████████
   /api/v1/users                            3,456 ████████████████
   /api/v1/comments                         2,345 ███████████
   /api/v1/categories                       1,234 ██████
   /api/v1/media                              890 ████

🚫 被阻止最多的 IP (Top 10):
   192.168.1.100               156 ██████████████████████████████████████████████████
   10.0.0.50                    89 █████████████████████████████
   172.16.0.25                  45 ██████████████

⚠️  被阻止最多的端点 (Top 10):
   /api/v1/articles                          234 ██████████████████████████████████████████████████
   /api/v1/users                              67 █████████████████
   /api/v1/comments                           43 ███████████

📅 请求时间分布 (最近24小时):
   2026-05-01 00:00     234 ██████████
   2026-05-01 01:00     189 ████████
   2026-05-01 02:00     145 ██████
   ...

================================================================================
```

---

## 命令说明

### 1. 生成报告

**基本用法：**

```bash
python scripts/rate_limit_monitor.py report
```

**保存统计数据：**

```bash
python scripts/rate_limit_monitor.py report --save
```

**显示内容：**

- ✅ 总体统计（总请求、允许/阻止数量）
- ✅ 热门 API 端点排行
- ✅ 被阻止最多的 IP 地址
- ✅ 被阻止最多的端点
- ✅ 24小时请求时间分布

---

### 2. 实时监控

**基本用法（默认 5 秒刷新）：**

```bash
python scripts/rate_limit_monitor.py watch
```

**自定义刷新间隔：**

```bash
python scripts/rate_limit_monitor.py watch -i 10
```

**特性：**

- ✅ 实时数据更新
- ✅ 自动告警检测
- ✅ 可视化图表

---

### 3. 检查告警

**基本用法（默认阈值 20%）：**

```bash
python scripts/rate_limit_monitor.py alert
```

**自定义阈值：**

```bash
python scripts/rate_limit_monitor.py alert --threshold 15.0
```

**输出示例：**

```
🚨 发现 3 个告警:

[WARNING] API 阻止率过高: 25.34% (阈值: 20.0%)
[CRITICAL] 可疑 IP 大量请求: 192.168.1.100 (156 次被阻止)
[WARNING] 端点被频繁限流: /api/v1/articles (234 次)
```

---

## 日志格式

速率限制日志文件：`logs/rate_limit.log`

**日志格式（JSON Lines）：**

```json
{"timestamp": "2026-05-01T14:30:22", "ip": "192.168.1.100", "endpoint": "/api/v1/articles", "method": "GET", "blocked": true, "reason": "rate_limit_exceeded"}
{"timestamp": "2026-05-01T14:30:23", "ip": "10.0.0.50", "endpoint": "/api/v1/users", "method": "POST", "blocked": false}
```

**字段说明：**

| 字段        | 类型      | 说明           |
|-----------|---------|--------------|
| timestamp | string  | ISO 8601 时间戳 |
| ip        | string  | 客户端 IP 地址    |
| endpoint  | string  | API 端点路径     |
| method    | string  | HTTP 方法      |
| blocked   | boolean | 是否被阻止        |
| reason    | string  | 阻止原因（可选）     |

---

## 集成到 FastAPI

### 1. 添加日志中间件

在 `src/auth/security_middleware.py` 中添加：

```python
import json
from pathlib import Path

class RateLimitLoggingMiddleware(BaseHTTPMiddleware):
    """速率限制日志中间件"""
    
    def __init__(self, app, log_file: str = "logs/rate_limit.log"):
        super().__init__(app)
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def dispatch(self, request: Request, call_next):
        # 记录请求
        start_time = time.time()
        response = await call_next(request)
        
        # 获取速率限制信息
        rate_limit_info = request.state.rate_limit if hasattr(request.state, 'rate_limit') else None
        
        if rate_limit_info:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "ip": request.client.host,
                "endpoint": str(request.url.path),
                "method": request.method,
                "blocked": rate_limit_info.get("blocked", False),
                "reason": rate_limit_info.get("reason", ""),
                "response_time": time.time() - start_time
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        
        return response
```

### 2. 注册中间件

在 `main.py` 或 `src/app.py` 中：

```python
from src.auth.security_middleware import RateLimitLoggingMiddleware

app.add_middleware(RateLimitLoggingMiddleware)
```

---

## 告警级别

### 🟢 正常 (INFO)

- 阻止率 < 5%
- 单 IP 被阻止次数 < 50
- 单端点被阻止次数 < 20

### 🟡 警告 (WARNING)

- 阻止率 5-20%
- 单 IP 被阻止次数 50-100
- 单端点被阻止次数 20-50

### 🔴 严重 (CRITICAL)

- 阻止率 > 20%
- 单 IP 被阻止次数 > 100
- 检测到 DDoS 攻击模式

---

## 最佳实践

### 1. 定期生成报告

**Cron 定时任务：**

```bash
# 每小时生成报告
0 * * * * cd /opt/fastblog && python scripts/rate_limit_monitor.py report --save >> logs/monitor_report.log 2>&1

# 每天发送摘要邮件
0 9 * * * cd /opt/fastblog && python scripts/rate_limit_monitor.py alert --threshold 10 | mail -s "Daily Rate Limit Report" admin@example.com
```

### 2. 设置合理的阈值

**开发环境：**

```bash
python scripts/rate_limit_monitor.py alert --threshold 30.0
```

**生产环境：**

```bash
python scripts/rate_limit_monitor.py alert --threshold 10.0
```

**高安全环境：**

```bash
python scripts/rate_limit_monitor.py alert --threshold 5.0
```

### 3. 分析异常模式

**识别 DDoS 攻击：**

```python
# 查找短时间内大量请求的 IP
def detect_ddos(entries, window_minutes=5, threshold=100):
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    ip_requests = defaultdict(list)
    
    for entry in entries:
        ip = entry['ip']
        timestamp = datetime.fromisoformat(entry['timestamp'])
        ip_requests[ip].append(timestamp)
    
    suspicious_ips = []
    
    for ip, timestamps in ip_requests.items():
        timestamps.sort()
        
        for i in range(len(timestamps)):
            window_end = timestamps[i] + timedelta(minutes=window_minutes)
            count = sum(1 for t in timestamps[i:] if t <= window_end)
            
            if count >= threshold:
                suspicious_ips.append({
                    'ip': ip,
                    'count': count,
                    'window': window_minutes
                })
                break
    
    return suspicious_ips
```

### 4. 自动封禁恶意 IP

**集成防火墙：**

```python
def block_suspicious_ips(stats, threshold=100):
    """自动封禁可疑 IP"""
    import subprocess
    
    blocked_ips = []
    
    for ip, count in stats["top_blocked_ips"].items():
        if count > threshold:
            # 使用 iptables 封禁
            subprocess.run([
                "iptables", "-A", "INPUT",
                "-s", ip,
                "-j", "DROP"
            ])
            blocked_ips.append(ip)
            print(f"🚫 Blocked IP: {ip} ({count} requests)")
    
    return blocked_ips
```

---

## 故障排查

### 问题 1: 没有日志数据

**症状：**

```
⚠️  日志文件不存在: logs/rate_limit.log
```

**解决：**

1. 确认中间件已正确注册
2. 检查日志目录权限
3. 验证是否有 API 请求产生

```bash
# 检查目录权限
ls -la logs/

# 手动创建日志文件
touch logs/rate_limit.log
chmod 644 logs/rate_limit.log
```

### 问题 2: 日志格式错误

**症状：**

```
JSONDecodeError: Expecting value
```

**解决：**

检查日志文件格式是否正确：

```bash
# 查看最后几行
tail -n 5 logs/rate_limit.log

# 验证 JSON 格式
python -c "import json; [json.loads(line) for line in open('logs/rate_limit.log')]"
```

### 问题 3: 性能影响

**症状：**

应用响应变慢

**解决：**

1. 使用异步日志写入
2. 批量写入日志
3. 限制日志文件大小

```python
# 使用异步日志
import asyncio

async def write_log_async(log_entry):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, write_log_sync, log_entry)
```

---

## 高级用法

### 1. 导出为 CSV

```python
import csv

def export_to_csv(entries, output_file="rate_limit_report.csv"):
    """导出为 CSV 格式"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'ip', 'endpoint', 'method', 'blocked'])
        writer.writeheader()
        writer.writerows(entries)
    
    print(f"✅ 导出完成: {output_file}")
```

### 2. 生成可视化图表

```python
import matplotlib.pyplot as plt

def generate_chart(stats):
    """生成可视化图表"""
    # 时间分布图
    hours = list(stats["by_hour"].keys())[-24:]
    counts = [stats["by_hour"][h] for h in hours]
    
    plt.figure(figsize=(12, 6))
    plt.plot(hours, counts, marker='o')
    plt.title("API Requests Over Time")
    plt.xlabel("Hour")
    plt.ylabel("Requests")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("rate_limit_chart.png")
    plt.show()
```

### 3. 集成 Prometheus

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNTER = Counter('api_requests_total', 'Total API requests', ['endpoint', 'status'])
RESPONSE_TIME = Histogram('api_response_seconds', 'Response time')

# 在中间件中记录
REQUEST_COUNTER.labels(endpoint=endpoint, status="blocked" if blocked else "allowed").inc()
RESPONSE_TIME.observe(response_time)
```

---

## 相关资源

- [速率限制系统增强](../docs/RATE_LIMITING.md)
- [系统监控工具](./SYSTEM_MONITORING.md)
- [部署指南](./DEPLOYMENT_GUIDE.md)
- [安全加固](./SECURITY_HARDENING.md)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
