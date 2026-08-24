# -*- coding: utf-8 -*-
"""
FastAPI 应用入口点（精简版）
"""

import argparse
import os
import signal
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 全局 FastAPI 应用实例（供外部工具使用）
app = None

# 使用统一的日志系统
from src.unified_logger import default_logger as logger


def parse_arguments():
    parser = argparse.ArgumentParser(description='启动 FastBlog 应用')
    parser.add_argument('--mode', choices=['app', 'supervisor'], default='app')
    parser.add_argument('--port', type=int, default=9421)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--nolog', action='store_true', default=False)
    parser.add_argument('--env', choices=['prod', 'dev', 'test'], default='prod')
    parser.add_argument('--workers', type=int, default=int(os.environ.get('WORKERS', '1')),
                        help='工作进程数（>1 时启用多 worker，需配置 Redis 共享限流/缓存）')
    return parser.parse_args()


def setup_signal_handlers():
    def handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在退出...")
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def run_supervisor_mode():
    try:
        from process_supervisor.supervisor_launcher import SupervisedLauncher
        supervisor = SupervisedLauncher()
        supervisor.setup_signal_handlers()
        if not supervisor.start_system():
            logger.error("监督器启动失败")
            sys.exit(1)
        supervisor.monitor_system()
    except Exception as e:
        logger.error(f"监督器运行异常: {e}")
        sys.exit(1)


def main():
    setup_signal_handlers()
    args = parse_arguments()

    if args.mode == 'supervisor':
        run_supervisor_mode()
        return

    # 日志系统已由 unified_logger 初始化，无需再次初始化

    # 简要输出启动信息
    logger.info(f"启动 FastAPI 后端，端口 {args.port}，环境 {args.env}")

    # 选择配置并启动
    from src.setting import get_config_by_env
    from src.app import create_app
    config = get_config_by_env(args.env)
    global app
    try:
        app = create_app(config)
    except Exception as e:
        import traceback
        logger.error(f"Error creating app: {e}")
        traceback.print_exc()
        sys.exit(1)

    try:
        import uvicorn
        # 使用模块级已创建的 app 实例（由顶层 create_app 调用产生）
        fastapi_app = app
        if fastapi_app is None:
            logger.error("FastAPI 应用实例创建失败")
            sys.exit(1)

        logger.info(f"FastAPI 应用已加载，准备启动服务器...")
        logger.info(f"服务器地址: http://{args.host}:{args.port} (workers={args.workers})")

        if args.workers > 1:
            # 多 worker 必须以 import 字符串方式启动（uvicorn 限制）。
            # 每个 worker 为独立进程，通过 Redis 共享限流/缓存，
            # 定时任务由 Redis 分布式锁保证全局只执行一次。
            uvicorn.run(
                "main:app",
                host=args.host,
                port=args.port,
                log_level="info",
                reload=False,
                workers=args.workers,
            )
        else:
            uvicorn.run(
                fastapi_app,
                host=args.host,
                port=args.port,
                log_level="info",  # 始终使用 info 级别以便看到启动信息
                reload=False,  # 禁用 reload 以避免多进程问题
                workers=1,  # 单 worker
            )
    except KeyboardInterrupt:
        logger.info("服务器已关闭")
    except Exception as e:
        logger.error(f"FastAPI 启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
