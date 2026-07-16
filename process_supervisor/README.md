# FastBlog 进程监督器

多进程管理系统，提供自动故障恢复、健康检查、集中监控等功能。

## 快速开始

```bash
# 启动监督器模式
python main.py --mode supervisor --env prod

# 启动 Web 管理界面（可选）
python process_supervisor/start_web_admin.py
# 访问 http://127.0.0.1:9422
```

## 管理的进程

| 进程              | 描述          | 端口   |
|-----------------|-------------|------|
| `main_app`      | FastAPI 主应用 | 9421 |
| `update_server` | 更新检查服务      | 8001 |

配置文件：`process_supervisor/supervisor_config.json`

## 核心功能

- **自动故障恢复** — 进程崩溃自动重启，指数退避延迟
- **三层健康检查** — 进程存活 / 端口监听 / HTTP 端点
- **日志聚合** — 每 5 分钟聚合所有进程日志
- **实时监控** — CPU / 内存 / 运行时间
- **Web 管理界面** — 可视化仪表盘 + REST API

## Web API

```bash
GET  /api/system/status           # 系统状态
GET  /api/processes               # 所有进程状态
POST /api/process/{name}/start    # 启动进程
POST /api/process/{name}/stop     # 停止进程
POST /api/process/{name}/restart  # 重启进程
```

API 文档：http://127.0.0.1:9422/docs
