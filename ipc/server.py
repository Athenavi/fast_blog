#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPC服务器模块
作为独立进程运行，提供进程间通信服务
"""

import logging
import signal
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from ipc import ProcessManager

logger = logging.getLogger(__name__)

class IPCServerProcess:
    """IPC服务器进程类"""
    
    def __init__(self):
        self.process_manager = None
        self.running = False
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在关闭IPC服务器...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows特定信号
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    def initialize(self):
        """初始化IPC服务器"""
        try:
            # 创建进程管理器（作为服务器）
            self.process_manager = ProcessManager("ipc_server", start_server=True)
            logger.info("IPC服务器初始化完成")
            return True
        except Exception as e:
            logger.error(f"IPC服务器初始化失败: {e}")
            return False
    
    def register_callbacks(self):
        """注册消息回调函数"""
        if not self.process_manager:
            return
            
        def handle_version_query(message):
            """处理版本查询请求"""
            logger.info("收到版本查询请求")
            
            # 返回版本信息
            version_info = {
                "backend_version": "V0.0.0.2",
                "frontend_version": "0.1.0",
                "build_time": "2026-02-12T08:04:22Z",
                "framework": "FastAPI 0.128.0",
                "status": "running"
            }
            
            # 发送响应
            if hasattr(message.data, 'get') and message.data.get('request_id'):
                self.process_manager.send_response(
                    message.data['request_id'], 
                    version_info
                )
        
        def handle_status_request(message):
            """处理状态查询请求"""
            logger.info("收到状态查询请求")
            
            status_info = {
                "ipc_server": "running",
                "timestamp": time.time(),
                "uptime": time.time() - getattr(self, 'start_time', time.time())
            }
            
            if hasattr(message.data, 'get') and message.data.get('request_id'):
                self.process_manager.send_response(
                    message.data['request_id'],
                    status_info
                )
        
        # 注册回调函数
        self.process_manager.register_callback("version_query", handle_version_query)
        self.process_manager.register_callback("status_request", handle_status_request)
        logger.info("消息回调函数注册完成")
    
    def run(self):
        """运行IPC服务器"""
        self.setup_signal_handlers()
        self.start_time = time.time()
        
        if not self.initialize():
            return False
            
        self.register_callbacks()
        self.running = True
        
        logger.info("IPC服务器已启动，等待连接...")
        
        try:
            # 保持服务器运行
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        finally:
            self.shutdown()
        
        return True
    
    def shutdown(self):
        """关闭IPC服务器"""
        if not self.running:
            return
            
        logger.info("正在关闭IPC服务器...")
        self.running = False
        
        if self.process_manager:
            self.process_manager.shutdown()
        
        logger.info("IPC服务器已关闭")

def main():
    """IPC服务器入口函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/ipc_server.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info("=== IPC服务器启动 ===")
    
    server = IPCServerProcess()
    success = server.run()
    
    if success:
        logger.info("IPC服务器正常退出")
        sys.exit(0)
    else:
        logger.error("IPC服务器启动失败")
        sys.exit(1)

if __name__ == "__main__":
    main()