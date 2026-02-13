# -*- coding: utf-8 -*-
"""
FastAPI应用入口点
支持独立启动器调用的版本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

import socket
import logging
import glob
import signal
import threading
import time

from src.logger_config import init_pythonanywhere_logger, init_optimized_logger

# 导入进程间通信模块
try:
    from ipc import get_process_manager, MessageType
    IPC_AVAILABLE = True
except ImportError:
    IPC_AVAILABLE = False
    logging.warning("IPC模块不可用，将使用基本启动模式")

# 为外部工具提供全局FastAPI应用实例
try:
    from src.app import create_app
    from src.setting import ProductionConfig, DevelopmentConfig, TestingConfig
    import argparse
    
    # 解析命令行参数以确定环境配置
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', type=str, choices=['prod', 'dev', 'test', 'production', 'development', 'testing'],
                        default='prod', help='指定运行环境: prod/dev/test (默认: prod)')
    # 解析已知参数，忽略未知参数
    args, _ = parser.parse_known_args()
    
    # 根据环境参数选择配置类
    if args.env in ['dev', 'development']:
        config = DevelopmentConfig()
    elif args.env in ['test', 'testing']:
        config = TestingConfig()
    else:
        config = ProductionConfig()  # 默认使用生产环境配置
    
    # 创建全局应用实例供外部工具使用
    app = create_app(config)
except Exception as e:
    # 如果创建失败，设置为None，避免影响正常的main()函数运行
    import traceback
    print(f"全局应用实例创建失败: {e}")
    traceback.print_exc()
    app = None


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动FastBlog应用程序')
    parser.add_argument('--mode', type=str, choices=['app', 'supervisor'],
                        default='app', help='启动模式: app(标准应用)/supervisor(进程监督器)')
    parser.add_argument('--port', type=int, default=9421,
                        help='应用程序运行的端口号 (默认: 9421)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='绑定主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--update', action='store_true',
                        help='启动前执行更新检查')
    parser.add_argument('--update-only', action='store_true',
                        help='仅执行更新而不启动服务器')
    parser.add_argument('--nolog', action='store_true', default=False,
                        help='禁用日志文件')
    parser.add_argument('--env', type=str, choices=['prod', 'dev', 'test', 'production', 'development', 'testing'],
                        default='prod', help='指定运行环境: prod/dev/test (默认: prod)')
    parser.add_argument('--guide', action='store_true', default=False,
                        help='强制启动系统初始化引导 (默认: False)')
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


def run_update():
    """执行更新程序"""
    logging.info("正在检查更新...")
    try:
        # 使用新的更新管理器
        from src.update.manager import update_manager
        
        # 启动更新（使用占位符数据）
        task_id = update_manager.start_update(
            update_type="full",
            target_version="latest", 
            source_url="https://example.com/update.zip"
        )
        
        if task_id:
            logging.info(f"更新任务已创建: {task_id}")
            
            # 监控更新进度
            def progress_callback(status):
                logging.info(f"更新进度: {status['progress']}% - {status['message']}")
            
            result = update_manager.monitor_update(task_id, progress_callback)
            if result:
                return result['status'] == 'completed'
            else:
                logging.error("更新监控失败")
                return False
        else:
            logging.error("创建更新任务失败")
            return False
            
    except Exception as e:
        logging.error(f"更新过程中出错: {str(e)}")
        return False


# 根据环境参数选择配置类
from src.setting import ProductionConfig, DevelopmentConfig, TestingConfig


def get_config_by_env(env):
    # 支持简写和完整形式
    if env in ['prod', 'production']:
        return ProductionConfig()
    elif env in ['dev', 'development']:
        return DevelopmentConfig()
    elif env in ['test', 'testing']:
        return TestingConfig()
    else:
        return ProductionConfig()  # 默认使用生产环境配置


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
        if IPC_AVAILABLE:
            pm = get_process_manager("main")
            pm.request_shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def setup_ipc_communication():
    """设置IPC通信"""
    if not IPC_AVAILABLE:
        return None
        
    try:
        pm = get_process_manager("main")
        
        # 注册消息回调
        def handle_shutdown_request(message):
            logging.info("收到关闭请求，正在关闭服务器...")
            # 这里应该通知uvicorn优雅关闭
            os.kill(os.getpid(), signal.SIGTERM)
            
        def handle_heartbeat(message):
            logging.debug(f"收到心跳消息: {message.data}")
            # 回复心跳
            pm.send_heartbeat()
            
        pm.register_callback(MessageType.SHUTDOWN_REQUEST.value, handle_shutdown_request)
        pm.register_callback(MessageType.HEARTBEAT.value, handle_heartbeat)
        
        # 启动心跳线程
        def heartbeat_thread():
            while True:
                try:
                    pm.send_heartbeat()
                    time.sleep(30)  # 每30秒发送一次心跳
                except Exception as e:
                    logging.error(f"心跳发送失败: {e}")
                    break
                    
        threading.Thread(target=heartbeat_thread, daemon=True).start()
        
        return pm
    except Exception as e:
        logging.error(f"IPC通信设置失败: {e}")
        return None


def run_supervisor_mode():
    """运行进程监督器模式"""
    try:
        from supervisor_launcher import SupervisedLauncher
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
    if not os.path.isfile(".env") or args.guide:
        logging.info("=" * 60)
        if not os.path.isfile(".env"):
            logging.info("检测到系统未初始化")
            logging.info("=" * 60)

        return

    # 初始化日志系统
    if args.nolog:
        logger = init_pythonanywhere_logger()
        if logger is None:
            logging.error("无日志环境下日志系统初始化失败")
            sys.exit(1)
        logging.info("无日志环境下日志系统已启动")
    else:
        logger = init_optimized_logger()
        if logger is None:
            logging.error("日志系统初始化失败")
            sys.exit(1)
        logging.info("日志系统已启动")

    # 处理更新选项
    if args.update_only:
        if not run_update():
            logger.error("更新失败，程序将退出")
            sys.exit(1)
        return

    if args.update:
        if not run_update():
            logger.warning("更新失败，继续使用当前版本启动")

    # 注意：数据库初始化现在在 src/app.py 的 lifespan 事件处理器中统一处理
    # 以确保无论通过何种方式启动应用都能正确执行

    # 检查端口可用性
    final_port = args.port
    if not is_port_available(final_port, args.host):
        logger.warning(f"端口 {final_port} 已被占用")

    # 设置IPC通信
    ipc_manager = setup_ipc_communication()
    
    # IPC通信初始化
    if ipc_manager:
        logger.info("IPC通信已建立")
    
    # 显示启动信息
    logger.info("=" * 50)
    logger.info("FastAPI应用程序正在启动...")
    logger.info(f"服务地址: http://{args.host}:{final_port}")
    logger.info(f"内部地址: http://127.0.0.1:{final_port}")
    logger.info(f"运行环境: {args.env}")
    if ipc_manager:
        logger.info("IPC通信已启用")
    logger.info("=" * 50)

    # 在启动服务前使用已创建的应用
    try:
        config = get_config_by_env(args.env)
        from src.app import create_app
        app_instance = create_app(config)

        # 使用 uvicorn 启动 FastAPI 应用
        import uvicorn
        logger.info("使用 uvicorn 启动 FastAPI 应用")
        logger.info(f"运行环境配置: {args.env}")
        
        # IPC通信状态更新
        if ipc_manager:
            logger.info("服务器已准备就绪")
        
        uvicorn.run(
            app_instance,
            host=args.host,
            port=final_port,
            log_level="info" if args.env in ['dev', 'development'] else "error",
            reload=args.env in ['dev', 'development']  # 只在开发模式下启用重载
        )

    except KeyboardInterrupt:
        logger.info("\n服务器正在关闭...")
        if ipc_manager:
            ipc_manager.request_shutdown()
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
        if ipc_manager:
            logger.error("IPC通信错误")
        sys.exit(1)
    finally:
        # 清理IPC资源
        if IPC_AVAILABLE:
            from ipc import cleanup_process_manager
            cleanup_process_manager()


if __name__ == '__main__':
    main()
