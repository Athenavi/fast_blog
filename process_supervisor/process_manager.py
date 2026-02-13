#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程管理器
负责启动、监控和管理所有子进程
"""

import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    """进程状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    RESTARTING = "restarting"

@dataclass
class ProcessConfig:
    """进程配置"""
    name: str
    command: List[str]
    working_dir: str = "."
    autostart: bool = True
    autorestart: bool = True
    restart_limit: int = 3
    restart_delay: int = 5  # 秒
    stdout_logfile: Optional[str] = None
    stderr_logfile: Optional[str] = None
    environment: Dict[str, str] = None

class ManagedProcess:
    """被管理的进程"""
    
    def __init__(self, config: ProcessConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.status = ProcessStatus.STOPPED
        self.restart_count = 0
        self.last_start_time = 0
        self.stdout_log = None
        self.stderr_log = None
        
    def start(self) -> bool:
        """启动进程"""
        if self.status in [ProcessStatus.RUNNING, ProcessStatus.STARTING]:
            logger.warning(f"进程 {self.config.name} 已在运行")
            return True
            
        try:
            self.status = ProcessStatus.STARTING
            self.last_start_time = time.time()
            
            # 准备日志文件
            if self.config.stdout_logfile:
                self.stdout_log = open(self.config.stdout_logfile, 'a', encoding='utf-8')
            if self.config.stderr_logfile:
                self.stderr_log = open(self.config.stderr_logfile, 'a', encoding='utf-8')
            
            # 设置环境变量
            env = os.environ.copy()
            if self.config.environment:
                env.update(self.config.environment)
            
            # 启动进程
            self.process = subprocess.Popen(
                self.config.command,
                cwd=self.config.working_dir,
                stdout=self.stdout_log or subprocess.PIPE,
                stderr=self.stderr_log or subprocess.PIPE,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            self.status = ProcessStatus.RUNNING
            self.restart_count = 0
            logger.info(f"进程 {self.config.name} 启动成功，PID: {self.process.pid}")
            return True
            
        except Exception as e:
            self.status = ProcessStatus.FAILED
            logger.error(f"启动进程 {self.config.name} 失败: {e}")
            return False
    
    def stop(self, timeout: int = 10) -> bool:
        """停止进程"""
        if not self.process or self.status not in [ProcessStatus.RUNNING, ProcessStatus.STARTING]:
            return True
            
        try:
            self.status = ProcessStatus.STOPPING
            
            # 发送终止信号
            if os.name == 'nt':
                # Windows使用taskkill
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], 
                             capture_output=True)
            else:
                # Unix/Linux使用SIGTERM
                self.process.terminate()
                try:
                    self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(f"进程 {self.config.name} 未在 {timeout} 秒内停止，强制终止")
                    self.process.kill()
                    self.process.wait()
            
            # 清理资源
            if self.stdout_log:
                self.stdout_log.close()
            if self.stderr_log:
                self.stderr_log.close()
                
            self.process = None
            self.status = ProcessStatus.STOPPED
            logger.info(f"进程 {self.config.name} 已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止进程 {self.config.name} 失败: {e}")
            self.status = ProcessStatus.FAILED
            return False
    
    def is_running(self) -> bool:
        """检查进程是否正在运行"""
        if not self.process:
            return False
            
        try:
            # 检查进程是否还在运行
            if self.process.poll() is None:
                return True
            else:
                # 进程已退出
                self.status = ProcessStatus.STOPPED
                return False
        except Exception:
            self.status = ProcessStatus.FAILED
            return False
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取进程状态信息"""
        return {
            'name': self.config.name,
            'status': self.status.value,
            'pid': self.process.pid if self.process else None,
            'restart_count': self.restart_count,
            'uptime': time.time() - self.last_start_time if self.last_start_time else 0
        }

class ProcessSupervisor:
    """进程监督器主类"""
    
    def __init__(self, config_file: str = None):
        self.processes: Dict[str, ManagedProcess] = {}
        self.config_file = config_file
        self.running = False
        self.monitor_thread = None
        self.ipc_port = 12345
        
        # 加载配置
        self._load_configuration()
        
    def _load_configuration(self):
        """加载进程配置"""
        default_configs = [
            ProcessConfig(
                name="ipc_server",
                command=[sys.executable, "-m", "ipc.server"],
                working_dir=".",
                autostart=True,
                autorestart=True,
                stdout_logfile="logs/ipc_server.log",
                stderr_logfile="logs/ipc_server.err.log"
            ),
            ProcessConfig(
                name="update_server",
                command=[sys.executable, "-m", "update_server.server"],
                working_dir=".",
                autostart=True,
                autorestart=True,
                stdout_logfile="logs/update_server.log",
                stderr_logfile="logs/update_server.err.log"
            ),
            ProcessConfig(
                name="main_app",
                command=[sys.executable, "main.py"],
                working_dir=".",
                autostart=True,
                autorestart=True,
                stdout_logfile="logs/main_app.log",
                stderr_logfile="logs/main_app.err.log"
            )
        ]
        
        for config in default_configs:
            self.processes[config.name] = ManagedProcess(config)
    
    def start_all_processes(self) -> bool:
        """启动所有配置的进程"""
        logger.info("开始启动所有进程...")
        success = True
        
        for name, process in self.processes.items():
            if process.config.autostart:
                if not process.start():
                    success = False
                    logger.error(f"启动进程 {name} 失败")
                else:
                    time.sleep(1)  # 给进程启动时间
        
        return success
    
    def stop_all_processes(self):
        """停止所有进程"""
        logger.info("开始停止所有进程...")
        
        for name, process in self.processes.items():
            process.stop()
    
    def start_process(self, name: str) -> bool:
        """启动指定进程"""
        if name not in self.processes:
            logger.error(f"进程 {name} 不存在")
            return False
            
        return self.processes[name].start()
    
    def stop_process(self, name: str) -> bool:
        """停止指定进程"""
        if name not in self.processes:
            logger.error(f"进程 {name} 不存在")
            return False
            
        return self.processes[name].stop()
    
    def restart_process(self, name: str) -> bool:
        """重启指定进程"""
        if name not in self.processes:
            logger.error(f"进程 {name} 不存在")
            return False
            
        process = self.processes[name]
        process.stop()
        time.sleep(1)
        return process.start()
    
    def get_process_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指定进程状态"""
        if name not in self.processes:
            return None
        return self.processes[name].get_status_info()
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有进程状态"""
        return {name: process.get_status_info() for name, process in self.processes.items()}
    
    def _monitor_processes(self):
        """监控进程运行状态"""
        while self.running:
            try:
                for name, process in self.processes.items():
                    # 检查进程是否意外退出
                    if process.config.autorestart and not process.is_running():
                        if process.status == ProcessStatus.RUNNING:
                            logger.warning(f"检测到进程 {name} 意外退出，准备重启")
                            process.restart_count += 1
                            
                            if process.restart_count <= process.config.restart_limit:
                                time.sleep(process.config.restart_delay)
                                if process.start():
                                    logger.info(f"进程 {name} 重启成功")
                                else:
                                    logger.error(f"进程 {name} 重启失败")
                            else:
                                logger.error(f"进程 {name} 达到最大重启次数限制")
                                process.status = ProcessStatus.FAILED
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"进程监控出错: {e}")
                time.sleep(10)
    
    def start_monitoring(self):
        """启动监控线程"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
            self.monitor_thread.start()
            logger.info("进程监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("进程监控已停止")
    
    def shutdown(self):
        """关闭监督器"""
        logger.info("正在关闭进程监督器...")
        self.stop_monitoring()
        self.stop_all_processes()
        logger.info("进程监督器已关闭")

# 全局监督器实例
_supervisor = None

def get_supervisor() -> ProcessSupervisor:
    """获取全局监督器实例"""
    global _supervisor
    if _supervisor is None:
        _supervisor = ProcessSupervisor()
    return _supervisor

def cleanup_supervisor():
    """清理全局监督器"""
    global _supervisor
    if _supervisor:
        _supervisor.shutdown()
        _supervisor = None