# FastBlog 进程监督器

## 概述

进程监督器是FastBlog系统的核心组件，负责统一管理所有子进程的生命周期。它借鉴了Supervisor的设计理念，提供可靠的进程监控、自动重启和集中管理功能。

## 架构设计

```
┌─────────────────┐
│  ProcessSupervisor │ (主监督器)
└─────────┬───────┘
          │
          ├──► IPC Server Process (端口: 12345)
          ├──► Update Checker Process (更新检查)
          ├──► Main App Process (核心应用)
          └──► Updater Process (更新器)
```

## 核心特性

### 1. 进程生命周期管理
- ✅ 自动启动配置的进程
- ✅ 监控进程运行状态
- ✅ 自动重启意外退出的进程
- ✅ 优雅的进程停止机制

### 2. 配置驱动
- ✅ JSON/YAML配置文件支持
- ✅ 灵活的进程配置选项
- ✅ 环境变量管理
- ✅ 日志文件配置

### 3. 监控与告警
- ✅ 实时进程状态监控
- ✅ 重启次数限制
- ✅ 详细的运行日志
- ✅ 健康检查机制

## 进程组件

### 1. IPC服务器进程
```
名称: ipc_server
职责: 提供进程间通信基础设施
端口: 12345
重启策略: 自动重启
日志: logs/ipc_server.log
```

### 2. 更新服务进程
```
名称: update_server
职责: 提供版本检查和状态服务
重启策略: 自动重启
日志: logs/update_server.log
```

### 3. 主应用进程
```
名称: main_app
职责: 核心业务逻辑处理
端口: 9421
重启策略: 自动重启
日志: logs/main_app.log
```

### 4. 更新器进程
```
名称: updater
职责: 执行应用更新操作
启动条件: 需要时手动启动
日志: logs/updater.log
```

## 配置说明

### 进程配置项

```python
ProcessConfig(
    name="进程名称",
    command=["命令", "参数1", "参数2"],  # 启动命令
    working_dir=".",                     # 工作目录
    autostart=True,                      # 是否自动启动
    autorestart=True,                    # 是否自动重启
    restart_limit=3,                     # 最大重启次数
    restart_delay=5,                     # 重启延迟(秒)
    stdout_logfile="logs/app.log",       # 标准输出日志
    stderr_logfile="logs/app.err.log",   # 错误输出日志
    environment={"KEY": "VALUE"}         # 环境变量
)
```

## 使用方法

### 1. 基本使用

```python
from process_supervisor import get_supervisor

# 获取监督器实例
supervisor = get_supervisor()

# 启动所有进程
supervisor.start_all_processes()

# 启动监控
supervisor.start_monitoring()

# 等待运行...
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    supervisor.shutdown()
```

### 2. 单独控制进程

```python
# 启动特定进程
supervisor.start_process("main_app")

# 停止特定进程
supervisor.stop_process("update_checker")

# 重启进程
supervisor.restart_process("ipc_server")

# 获取进程状态
status = supervisor.get_process_status("main_app")
print(status)
```

### 3. 批量操作

```python
# 获取所有进程状态
all_status = supervisor.get_all_status()
for name, status in all_status.items():
    print(f"{name}: {status['status']}")

# 停止所有进程
supervisor.stop_all_processes()
```

## API接口

### ProcessSupervisor 类

#### 启动控制
- `start_all_processes()` - 启动所有配置的进程
- `start_process(name)` - 启动指定进程
- `stop_all_processes()` - 停止所有进程
- `stop_process(name)` - 停止指定进程
- `restart_process(name)` - 重启指定进程

#### 状态查询
- `get_process_status(name)` - 获取单个进程状态
- `get_all_status()` - 获取所有进程状态

#### 监控管理
- `start_monitoring()` - 启动进程监控
- `stop_monitoring()` - 停止进程监控
- `shutdown()` - 关闭监督器

## 日志管理

### 日志目录结构
```
logs/
├── ipc_server.log          # IPC服务器输出日志
├── ipc_server.err.log      # IPC服务器错误日志
├── update_server.log      # 更新服务输出日志
├── update_server.err.log  # 更新服务错误日志
├── main_app.log           # 主应用输出日志
├── main_app.err.log       # 主应用错误日志
└── supervisor.log         # 监督器自身日志
```

### 日志轮转
建议配置日志轮转以避免日志文件过大：
```bash
# 使用logrotate配置
/var/log/fastblog/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

## 故障排除

### 常见问题

1. **进程启动失败**
   - 检查命令路径是否正确
   - 确认工作目录存在
   - 查看错误日志文件

2. **进程频繁重启**
   - 检查重启次数是否达到限制
   - 查看应用是否有致命错误
   - 调整restart_delay参数

3. **监控线程异常**
   - 查看supervisor.log日志
   - 确认主进程没有被意外终止

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 手动检查进程状态
supervisor = get_supervisor()
for name, process in supervisor.processes.items():
    print(f"{name}: {process.status}")
    print(f"  Running: {process.is_running()}")
    print(f"  PID: {process.process.pid if process.process else 'None'}")
```

## 最佳实践

1. **配置管理**
   - 使用配置文件而非硬编码
   - 为不同环境准备不同的配置
   - 定期备份配置文件

2. **日志管理**
   - 启用详细的日志记录
   - 定期清理旧日志文件
   - 监控日志文件大小

3. **监控告警**
   - 设置进程健康检查
   - 配置异常通知机制
   - 定期检查重启次数

4. **安全考虑**
   - 限制进程运行权限
   - 验证启动命令的安全性
   - 定期更新依赖包

## 扩展功能

### 计划中的功能
- [ ] Web管理界面
- [ ] RESTful API接口
- [ ] 邮件/SMS告警通知
- [ ] 进程依赖关系管理
- [ ] 动态配置更新
- [ ] 性能监控和统计

### 插件系统
支持通过插件扩展监督器功能：
```python
# 示例：自定义健康检查插件
class CustomHealthChecker:
    def check_health(self, process_name, process_info):
        # 自定义健康检查逻辑
        pass
```