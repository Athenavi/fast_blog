# -*- coding: utf-8 -*-
"""
FastAPI 应用入口点（精简版）
"""

import os
import sys
import logging
import signal
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 全局 FastAPI 应用实例（供外部工具使用）
try:
    # 确保 Django 设置在导入任何应用代码之前就已经设置
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
    import django

    if not hasattr(django, '_setup_complete') or not django.apps.apps.ready:
        try:
            django.setup()
            django._setup_complete = True
            print("[Main] Django setup completed successfully")
        except RuntimeError as e:
            if "populate() isn't reentrant" not in str(e):
                raise
            else:
                print("[Main] Django already initialized")
    
    from src.app import create_app
    from src.setting import ProductionConfig

    app = create_app(ProductionConfig())
    print("[Main] FastAPI app created successfully")
except Exception as e:
    import traceback
    print(f"[Main] Error creating app: {e}")
    traceback.print_exc()
    app = None

from src.logger_config import init_optimized_logger


def parse_arguments():
    parser = argparse.ArgumentParser(description='启动 FastBlog 应用')
    parser.add_argument('--mode', choices=['app', 'supervisor'], default='app')
    parser.add_argument('--backend', choices=['fastapi', 'django'], default='fastapi')
    parser.add_argument('--port', type=int, default=9421)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--nolog', action='store_true', default=False)
    parser.add_argument('--env', choices=['prod', 'dev', 'test'], default='prod')
    return parser.parse_args()


def setup_signal_handlers():
    def handler(signum, frame):
        logging.info(f"收到信号 {signum}，正在退出...")
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def run_supervisor_mode():
    try:
        from process_supervisor.supervisor_launcher import SupervisedLauncher
        supervisor = SupervisedLauncher()
        supervisor.setup_signal_handlers()
        if not supervisor.start_system():
            logging.error("监督器启动失败")
            sys.exit(1)
        supervisor.monitor_system()
    except Exception as e:
        logging.error(f"监督器运行异常: {e}")
        sys.exit(1)


def main():
    setup_signal_handlers()
    args = parse_arguments()

    if args.mode == 'supervisor':
        run_supervisor_mode()
        return

    # 初始化日志
    logger = init_optimized_logger()
    if not logger:
        logging.error("日志系统初始化失败")
        sys.exit(1)

    # 简要输出启动信息
    logging.info(f"启动 {args.backend.upper()} 后端，端口 {args.port}，环境 {args.env}")

    # 选择配置并启动
    from src.setting import get_config_by_env
    config = get_config_by_env(args.env)

    if args.backend == 'fastapi':
        try:
            import uvicorn
            # 使用应用实例而不是工厂函数
            from src.app import app as fastapi_app
            if fastapi_app is None:
                logging.error("FastAPI 应用实例创建失败")
                sys.exit(1)
            
            logging.info(f"FastAPI 应用已加载，准备启动服务器...")
            logging.info(f"服务器地址: http://{args.host}:{args.port}")
            
            uvicorn.run(
                fastapi_app,
                host=args.host,
                port=args.port,
                log_level="info",  # 始终使用 info 级别以便看到启动信息
                reload=False,  # 禁用 reload 以避免多进程问题
                workers=1,  # 使用单 worker 避免多进程问题
            )
        except KeyboardInterrupt:
            logging.info("服务器已关闭")
        except Exception as e:
            logging.error(f"FastAPI 启动失败: {e}")
            sys.exit(1)
    else:  # django
        try:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
            sys.argv = ['manage.py', 'runserver', f'{args.host}:{args.port}', '--noreload']
            from django.core.management import execute_from_command_line
            execute_from_command_line(sys.argv)
        except KeyboardInterrupt:
            logging.info("服务器已关闭")
        except Exception as e:
            logging.error(f"Django 启动失败: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
