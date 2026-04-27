# -*- coding: utf-8 -*-
"""
FastAPI 应用入口点
支持独立启动器调用的版本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Windows + asyncpg 兼容性修复：使用 SelectorEventLoop
if sys.platform == 'win32':
    import asyncio

    try:
        # 尝试使用 SelectorEventLoop（asyncpg 推荐）
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("[INFO] Windows: Using SelectorEventLoop for asyncpg compatibility")
    except Exception as e:
        print(f"[WARNING] Failed to set event loop policy: {e}")

import socket
import logging
import glob
import signal
import argparse

from src.logger_config import init_pythonanywhere_logger, init_optimized_logger

# 为外部工具提供全局 FastAPI 应用实例
try:
    # 先设置 Django settings 并初始化，避免导入错误
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
    
    from src.app import create_app
    from src.setting import ProductionConfig, DevelopmentConfig, TestingConfig

    # 根据环境参数选择配置类（使用默认值）
    config = ProductionConfig()  # 默认使用生产环境配置
    
    # 创建全局应用实例供外部工具使用
    app = create_app(config)
except Exception as e:
    # 如果创建失败，设置为 None，避免影响正常的 main() 函数运行
    import traceback

    print(f"全局应用实例创建失败：{e}")
    traceback.print_exc()
    app = None


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动 FastBlog 应用程序')
    parser.add_argument('--mode', type=str, choices=['app', 'supervisor'],
                        default='app', help='启动模式：app(标准应用)/supervisor(进程监督器)')
    parser.add_argument('--backend', type=str, choices=['fastapi', 'django'],
                        default='fastapi', help='后端框架选择：fastapi/django (默认：fastapi)')
    parser.add_argument('--port', type=int, default=9421,
                        help='应用程序运行的端口号 (默认：9421)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='绑定主机地址 (默认：0.0.0.0)')
    parser.add_argument('--nolog', action='store_true', default=False,
                        help='禁用日志文件')
    parser.add_argument('--env', type=str, choices=['prod', 'dev', 'test', 'production', 'development', 'testing'],
                        default='prod', help='指定运行环境：prod/dev/test (默认：prod)')
    return parser.parse_args()



def is_port_available(port, host='0.0.0.0'):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def get_user_port_input():
    """获取用户输入的端口号"""
    while True:
        try:
            user_port = int(input("请提供一个可用的端口号: "))
            if 1 <= user_port <= 65535:
                if is_port_available(user_port):
                    return user_port
                else:
                    print(f"端口 {user_port} 已被占用，请尝试其他端口。")
            else:
                print("端口号必须在 1-65535 范围内。")
        except ValueError:
            print("请输入有效的数字端口号。")

# 根据环境参数选择配置类
from src.setting import get_config_by_env


def execute_debug_scripts():
    """执行 debug 目录下的所有 Python 脚本"""
    global script_name
    debug_dir = os.path.join(os.path.dirname(__file__), 'debug')

    # 获取 debug 目录下所有 .py 文件
    debug_scripts = glob.glob(os.path.join(debug_dir, '*.py'))

    # 按文件名排序，确保按顺序执行
    debug_scripts.sort()

    logging.info("开始执行 debug 目录下的脚本...")
    for script_path in debug_scripts:
        try:
            script_name = os.path.basename(script_path)
            logging.info(f"正在执行: {script_name}")

            # 执行脚本并捕获输出，添加项目根目录到PYTHONPATH
            import subprocess
            import sys

            # 复制当前环境变量并添加项目根目录到PYTHONPATH
            env = os.environ.copy()
            debug_project_root = os.path.dirname(__file__)
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{debug_project_root};{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = debug_project_root

            result = subprocess.run([sys.executable, script_path],
                                    capture_output=True, text=True, cwd=os.path.dirname(__file__), env=env)

            if result.stdout:
                logging.info(f"{script_name} 输出:\n{result.stdout}")
            if result.stderr:
                logging.error(f"{script_name} 错误:\n{result.stderr}")

            logging.info(f"完成执行: {script_name} (返回码: {result.returncode})")
        except Exception as e:
            logging.error(f"执行 {script_name} 时出错: {str(e)}")

    logging.info("debug 目录下的脚本执行完成")


def setup_signal_handlers():
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logging.info(f"收到信号 {signum}，正在优雅关闭...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_supervisor_mode():
    """运行进程监督器模式"""
    try:
        from process_supervisor.supervisor_launcher import SupervisedLauncher
        supervisor = SupervisedLauncher()
        supervisor.setup_signal_handlers()
        
        if not supervisor.start_system():
            logging.error("监督器系统启动失败")
            sys.exit(1)
        
        supervisor.monitor_system()
        
    except ImportError as e:
        logging.error(f"导入监督器模块失败: {e}")
        logging.error("请确保在项目根目录下运行此脚本")
        sys.exit(1)
    except Exception as e:
        logging.error(f"监督器运行异常: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)

def main():
    # 设置信号处理器
    setup_signal_handlers()
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 根据模式选择不同的启动方式
    if args.mode == 'supervisor':
        logging.info("启动进程监督器模式...")
        run_supervisor_mode()
        return
    # app模式继续下面的标准流程

    # 检查配置文件是否存在或强制启动引导程序
    if not os.path.isfile(".env"):
        logging.info("=" * 60)
        logging.info("检测到系统未初始化")
        logging.info("将启动安装向导模式")
        logging.info("=" * 60)
        # 不退出，继续启动服务器以运行安装向导
        # 数据库初始化将在配置完成后进行

    # 初始化日志系统
    if args.nolog:
        logger = init_pythonanywhere_logger()
        if logger is None:
            logging.error("无日志环境下日志系统初始化失败")
            sys.exit(1)
        # 每个 worker 都输出自己的日志系统启动信息（带 worker 标识）
        from src.setting import _get_worker_info
        worker_info = _get_worker_info()
        logging.info(f"{worker_info} 无日志环境下日志系统已启动")
    else:
        logger = init_optimized_logger()
        if logger is None:
            logging.error("日志系统初始化失败")
            sys.exit(1)
        # 每个 worker 都输出自己的日志系统启动信息（带 worker 标识）
        from src.setting import _get_worker_info
        worker_info = _get_worker_info()
        logging.info(f"{worker_info} 日志系统已启动")

    # 注意：数据库初始化现在在 src/app.py 的 lifespan 事件处理器中统一处理
    # 以确保无论通过何种方式启动应用都能正确执行

    # 检查端口可用性
    final_port = args.port
    if not is_port_available(final_port, args.host):
        logger.warning(f"端口 {final_port} 已被占用")

    # 显示后端选择信息
    print_backend_info(args)

    # 根据选择的后端启动服务
    if args.backend == 'fastapi':
        # FastAPI 模式
        config = get_config_by_env(args.env)
        run_fastapi_backend(args, config, logger)
    else:
        # Django 模式
        run_django_backend(args)


def print_backend_info(args):
    """打印后端选择信息（只在主进程中输出）"""
    # 检查是否是主进程
    import multiprocessing
    try:
        current_process = multiprocessing.current_process()
        if current_process.name != 'MainProcess':
            return  # 非主进程不输出
    except Exception:
        pass
    
    # 每个 worker 都输出自己的启动信息（带 worker 标识）
    from src.setting import _get_worker_info
    worker_info = _get_worker_info()
    
    logging.info(f"{worker_info} " + "=" * 70)
    logging.info(f"{worker_info} 🚀 博客系统后端服务启动")
    logging.info(f"{worker_info} " + "=" * 70)
    logging.info(f"{worker_info} 选择的后端框架：{args.backend.upper()}")

    if args.backend == 'fastapi':
        logging.info(f"{worker_info} ")
        logging.info(f"{worker_info} 【FastAPI 模式 - 详细说明】")
        logging.info(f"{worker_info}   • 技术栈：FastAPI + SQLAlchemy (异步)")
        logging.info(f"{worker_info}   • API 路由：src/api/v1/*.py")
        logging.info(f"{worker_info}   • 认证方式：JWT Token (FastAPI Users)")
        logging.info(f"{worker_info}   • 数据库：PostgreSQL (异步连接)")
        logging.info(f"{worker_info}   • 适用场景：高性能 API 服务、微服务架构")
        logging.info(f"{worker_info} ")
        logging.info(f"{worker_info}   📌 可用端点:")
        logging.info(f"{worker_info}     - API 文档：http://{args.host}:{args.port}/docs")
        logging.info(f"{worker_info}     - 备用文档：http://{args.host}:{args.port}/redoc")
        logging.info(f"{worker_info}     - 健康检查：http://{args.host}:{args.port}/health")
        logging.info(f"{worker_info}     - 用户管理：http://{args.host}:{args.port}/api/v1/users/*")
        logging.info(f"{worker_info}     - 文章管理：http://{args.host}:{args.port}/api/v1/articles/*")
        logging.info(f"{worker_info}     - 分类管理：http://{args.host}:{args.port}/api/v1/categories/*")
        logging.info(f"{worker_info}     - 媒体管理：http://{args.host}:{args.port}/api/v1/media/*")
        logging.info(f"{worker_info}     - 仪表板：http://{args.host}:{args.port}/api/v1/dashboard/*")
    else:  # django
        logging.info(f"{worker_info} ")
        logging.info(f"{worker_info} 【Django 模式 - 详细说明】")
        logging.info(f"{worker_info}   • 技术栈：Django 6 + Django Ninja (FastAPI 风格)")
        logging.info(f"{worker_info}   • API 路由：src/api/v1/*.py (通过适配器转换)")
        logging.info(f"{worker_info}   • 认证方式：Django Session/Token")
        logging.info(f"{worker_info}   • 数据库：PostgreSQL (Django ORM)")
        logging.info(f"{worker_info}   • 适用场景：传统 Web 应用、快速开发、企业级项目")
        logging.info(f"{worker_info} ")
        logging.info(f"{worker_info}   📌 可用端点:")
        logging.info(f"{worker_info}     - Admin 后台：http://{args.host}:{args.port}/admin/")
        logging.info(f"{worker_info}     - API 文档：http://{args.host}:{args.port}/api/docs/")
        logging.info(f"{worker_info}     - Schema：http://{args.host}:{args.port}/api/schema/")
        logging.info(f"{worker_info}     - 测试页面：http://{args.host}:{args.port}/test-api/")
        logging.info(f"{worker_info}     - 用户管理：http://{args.host}:{args.port}/api/v1/users/*")
        logging.info(f"{worker_info}     - 文章管理：http://{args.host}:{args.port}/api/v1/articles/*")
        logging.info(f"{worker_info}     - 分类管理：http://{args.host}:{args.port}/api/v1/categories/*")
        logging.info(f"{worker_info}     - 媒体管理：http://{args.host}:{args.port}/api/v1/media/*")
        logging.info(f"{worker_info} ")
        logging.info(f"{worker_info}   [注意] Django 模式下不使用 dashboard 路由")
        logging.info(f"{worker_info}      (使用 Django 原生 Admin 后台 /admin/)")

    logging.info(f"{worker_info} ")
    logging.info(f"{worker_info} 运行端口：{args.port}")
    logging.info(f"{worker_info} 运行环境：{args.env}")
    logging.info(f"{worker_info} 主机地址：{args.host}")
    logging.info(f"{worker_info} " + "=" * 70)


def run_fastapi_backend(args, config, logger):
    """运行 FastAPI 后端"""
    try:
        # 使用 uvicorn 启动 FastAPI 应用
        import uvicorn
        
        # 只在主进程中输出启动日志（workers 由 app.py 中输出）
        import multiprocessing
        from src.setting import _get_worker_info
        
        current_process = multiprocessing.current_process()
        if current_process.name == 'MainProcess':
            worker_info = _get_worker_info()
            logger.info(f"{worker_info} 使用 uvicorn 启动 FastAPI 应用")
            logger.info(f"{worker_info} 运行环境配置：{args.env}")
            logger.info(f"{worker_info} 服务器已准备就绪")

        # 配置 uvicorn 参数
        uvicorn_config = {
            "app": "src.app:create_app",  # 使用字符串格式以启用 reload 和 workers
            "host": args.host,
            "port": args.port,
            "log_level": "info" if args.env in ['dev', 'development'] else "error",
            "reload": args.env in ['dev', 'development'],  # 开发环境启用热重载
            "workers": 1 if args.env in ['dev', 'development'] else 4,  # 开发环境单进程，生产环境多进程
            "loop": "auto",  # 自动选择事件循环（Windows 上会自动使用 ProactorEventLoop）
            "http": "auto",  # 自动选择 HTTP 协议实现
        }

        # 如果是开发环境，添加额外的调试配置
        if args.env in ['dev', 'development']:
            logger.info(f"{worker_info} [OK] 开发模式：已启用热重载 (reload=True)")
            logger.info(f"{worker_info} [OK] 开发模式：单进程运行 (workers=1)")
            logger.info(f"{worker_info} [OK] 访问 API 文档：http://localhost:9421/docs")
        else:
            logger.info(f"{worker_info} [OK] 生产模式：已启用多进程 (workers={uvicorn_config['workers']})")

        # 启动 uvicorn 服务器
        uvicorn.run(**uvicorn_config)

    except KeyboardInterrupt:
        logger.info("\n服务器正在关闭...")
    except Exception as e:
        logger.error(f"服务器启动失败：{str(e)}")
        sys.exit(1)


def run_django_backend(args):
    """运行 Django 后端"""
    try:
        import django
        from django.conf import settings
        from django.core.management import execute_from_command_line

        # 设置 Django 环境
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
        
        # 确保项目根目录在 sys.path 中
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # 设置 PYTHONPATH 环境变量，确保子进程也能找到模块
        current_pythonpath = os.environ.get('PYTHONPATH', '')
        if project_root not in current_pythonpath:
            if current_pythonpath:
                os.environ['PYTHONPATH'] = f"{project_root}{os.pathsep}{current_pythonpath}"
            else:
                os.environ['PYTHONPATH'] = project_root

        # 初始化 Django（防止重复初始化）
        if not hasattr(django, '_setup_complete') or not django.apps.apps.ready:
            try:
                django.setup()
                django._setup_complete = True
            except RuntimeError as e:
                if "populate() isn't reentrant" in str(e):
                    pass  # Django 已经初始化过了
                else:
                    raise

        logger = logging.getLogger(__name__)
        logger.info("Django 环境初始化完成")
        logger.info("启动 Django 开发服务器...")

        # 构建 Django 启动参数
        sys.argv = [
            'manage.py',
            'runserver',
            f'{args.host}:{args.port}',
            '--noreload'  # 始终禁用自动重载以避免子进程问题
        ]

        # 启动 Django 服务器
        execute_from_command_line(sys.argv)

    except KeyboardInterrupt:
        logging.info("\n服务器正在关闭...")
    except Exception as e:
        logging.error(f"Django 服务器启动失败：{str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
