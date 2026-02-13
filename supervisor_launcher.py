#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastBlog 进程监督器启动器
统一管理所有子进程的生命周期
"""

import logging
import signal
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from process_supervisor.process_manager import get_supervisor, ProcessSupervisor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/supervisor_launcher.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SupervisedLauncher:
    """监督式启动器"""
    
    def __init__(self):
        self.base_dir = project_root
        self.supervisor: ProcessSupervisor = None
        self.running = False
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在优雅关闭...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows特定信号
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    def initialize_supervisor(self) -> bool:
        """初始化进程监督器"""
        try:
            logger.info("初始化进程监督器...")
            self.supervisor = get_supervisor()
            
            # 自定义进程配置
            self._customize_process_configs()
            
            logger.info("进程监督器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化进程监督器失败: {e}")
            return False
    
    def _customize_process_configs(self):
        """自定义进程配置"""
        if not self.supervisor:
            return
            
        # 修改IPC服务器配置
        if "ipc_server" in self.supervisor.processes:
            ipc_process = self.supervisor.processes["ipc_server"]
            ipc_process.config.command = [sys.executable, "-m", "ipc.server"]
            ipc_process.config.working_dir = str(self.base_dir)
            
        # 修改更新检查器配置
        if "update_checker" in self.supervisor.processes:
            update_process = self.supervisor.processes["update_checker"]
            update_process.config.command = [sys.executable, "-m", "update_server.server"]
            update_process.config.working_dir = str(self.base_dir)
            # 更新检查器使用不同端口
            update_process.config.environment = {
                "UPDATE_CHECKER_PORT": "8001",
                "UPDATE_CHECKER_HOST": "127.0.0.1"
            }
            
        # 修改主应用配置
        if "main_app" in self.supervisor.processes:
            main_process = self.supervisor.processes["main_app"]
            main_process.config.command = [sys.executable, "main.py"]
            main_process.config.working_dir = str(self.base_dir)
    
    def start_system(self) -> bool:
        """启动整个系统"""
        logger.info("=== FastBlog 进程监督器启动 ===")
        
        # 初始化监督器
        if not self.initialize_supervisor():
            return False
        
        # 启动所有进程
        logger.info("启动所有子进程...")
        if not self.supervisor.start_all_processes():
            logger.error("启动子进程失败")
            return False
        
        # 启动监控
        self.supervisor.start_monitoring()
        
        # 等待系统稳定
        time.sleep(3)
        
        # 验证关键进程状态
        self._verify_processes()
        
        self.running = True
        logger.info("系统启动完成，所有进程已在监督下运行")
        return True
    
    def _verify_processes(self):
        """验证关键进程状态"""
        critical_processes = ["ipc_server", "main_app"]
        
        for process_name in critical_processes:
            if process_name in self.supervisor.processes:
                status = self.supervisor.get_process_status(process_name)
                if status and status['status'] == 'running':
                    logger.info(f"✓ {process_name} 运行正常 (PID: {status['pid']})")
                else:
                    logger.warning(f"⚠ {process_name} 状态异常: {status}")
    
    def monitor_system(self):
        """监控系统运行状态"""
        logger.info("进入系统监控模式...")
        
        try:
            while self.running:
                # 定期输出系统状态
                if int(time.time()) % 30 == 0:  # 每30秒输出一次
                    self._print_system_status()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        finally:
            self.shutdown()
    
    def _print_system_status(self):
        """打印系统状态"""
        if not self.supervisor:
            return
            
        statuses = self.supervisor.get_all_status()
        running_count = sum(1 for status in statuses.values() 
                           if status['status'] == 'running')
        
        logger.info(f"系统状态: {running_count}/{len(statuses)} 进程运行中")
        
        for name, status in statuses.items():
            uptime_str = f" (运行 {int(status['uptime'])}秒)" if status['uptime'] > 0 else ""
            logger.info(f"  {name}: {status['status']}{uptime_str}")
    
    def shutdown(self):
        """关闭系统"""
        if not self.running:
            return
            
        logger.info("正在关闭系统...")
        self.running = False
        
        if self.supervisor:
            self.supervisor.shutdown()
        
        logger.info("系统已完全关闭")

def main():
    """启动器入口函数"""
    try:
        launcher = SupervisedLauncher()
        launcher.setup_signal_handlers()
        
        # 启动系统
        if not launcher.start_system():
            logger.error("系统启动失败")
            sys.exit(1)
        
        # 进入监控模式
        launcher.monitor_system()
        
    except Exception as e:
        logger.error(f"启动器运行异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()