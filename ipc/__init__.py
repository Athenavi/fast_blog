#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastBlog 进程间通信模块
提供启动器、主程序、更新器之间的安全通信机制
"""

import json
import logging
import socket
import threading
import time
from enum import Enum
from queue import Queue, Empty
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """消息类型枚举"""
    STATUS_UPDATE = "status_update"
    UPDATE_REQUEST = "update_request"
    SHUTDOWN_REQUEST = "shutdown_request"
    HEARTBEAT = "heartbeat"
    VERSION_INFO = "version_info"
    VERSION_QUERY = "version_query"
    VERSION_FULL_INFO = "version_full_info"
    VERSION_FRONTEND_INFO = "version_frontend_info"
    VERSION_BACKEND_INFO = "version_backend_info"

class IPCMessage:
    """IPC消息类"""
    
    def __init__(self, msg_type: MessageType, data: Dict[str, Any] = None, sender: str = "unknown"):
        self.type = msg_type
        self.data = data or {}
        self.sender = sender
        self.timestamp = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "data": self.data,
            "sender": self.sender,
            "timestamp": self.timestamp
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPCMessage':
        """从字典创建消息对象"""
        return cls(
            msg_type=MessageType(data["type"]),
            data=data.get("data", {}),
            sender=data.get("sender", "unknown")
        )

class IPCServer:
    """IPC服务器类 - 接收消息"""
    
    def __init__(self, port: int = 12345, message_handler: Optional[Callable] = None):
        self.port = port
        self.message_handler = message_handler
        self.running = False
        self.server_socket = None
        self.client_sockets = []
        
    def start(self):
        """启动IPC服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"IPC服务器启动，监听端口: {self.port}")
            
            # 启动监听线程
            threading.Thread(target=self._listen_loop, daemon=True).start()
            
        except Exception as e:
            logger.error(f"启动IPC服务器失败: {e}")
            
    def _listen_loop(self):
        """监听连接循环"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.debug(f"新连接来自: {address}")
                
                # 为每个客户端启动处理线程
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                ).start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接时出错: {e}")
                    
    def _handle_client(self, client_socket):
        """处理客户端消息"""
        try:
            while self.running:
                # 接收消息长度
                length_bytes = client_socket.recv(4)
                if not length_bytes:
                    break
                    
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # 接收消息内容
                message_data = b''
                while len(message_data) < message_length:
                    chunk = client_socket.recv(message_length - len(message_data))
                    if not chunk:
                        break
                    message_data += chunk
                    
                if len(message_data) == message_length:
                    # 解析消息
                    message_dict = json.loads(message_data.decode('utf-8'))
                    message = IPCMessage.from_dict(message_dict)
                    
                    logger.debug(f"收到消息: {message.type.value} from {message.sender}")
                    
                    # 调用消息处理器
                    if self.message_handler:
                        try:
                            self.message_handler(message)
                        except Exception as e:
                            logger.error(f"处理消息时出错: {e}")
                            
        except Exception as e:
            logger.error(f"处理客户端连接时出错: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
                
    def stop(self):
        """停止IPC服务器"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logger.info("IPC服务器已停止")

class IPCClient:
    """IPC客户端类 - 发送消息"""
    
    def __init__(self, port: int = 12345):
        self.port = port
        self.socket = None
        
    def connect(self) -> bool:
        """连接到IPC服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('localhost', self.port))
            logger.debug("成功连接到IPC服务器")
            return True
        except Exception as e:
            logger.error(f"连接IPC服务器失败: {e}")
            return False
            
    def send_message(self, message: IPCMessage) -> bool:
        """发送消息"""
        try:
            if not self.socket:
                if not self.connect():
                    return False
                    
            # 序列化消息
            message_dict = message.to_dict()
            message_json = json.dumps(message_dict, ensure_ascii=False)
            message_bytes = message_json.encode('utf-8')
            
            # 发送消息长度（4字节）
            length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
            self.socket.send(length_bytes)
            
            # 发送消息内容
            self.socket.send(message_bytes)
            
            logger.debug(f"消息发送成功: {message.type.value}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
            
    def close(self):
        """关闭连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

class ProcessManager:
    """进程管理器 - 协调各组件通信"""
    
    def __init__(self, role: str = "main"):
        self.role = role
        self.ipc_port = 12345
        self.server = IPCServer(port=self.ipc_port, message_handler=self._handle_message)
        self.clients = {}  # 存储其他组件的客户端连接
        self.callbacks = {}  # 消息回调函数
        self.pending_requests = {}  # 存储待处理的请求 {request_id: Queue}
        self.request_counter = 0  # 请求ID计数器
        
        # 启动IPC服务器
        self.server.start()
        
    def _handle_message(self, message: IPCMessage):
        """处理接收到的消息"""
        message_type = message.type.value
        
        # 处理响应消息
        if hasattr(message.data, 'get') and message.data.get('response_to'):
            request_id = message.data['response_to']
            if request_id in self.pending_requests:
                self.pending_requests[request_id].put(message.data)
                return
        
        # 调用对应的回调函数
        if message_type in self.callbacks:
            try:
                self.callbacks[message_type](message)
            except Exception as e:
                logger.error(f"执行回调函数时出错: {e}")
                
    def register_callback(self, message_type: str, callback: Callable):
        """注册消息回调函数"""
        self.callbacks[message_type] = callback
        
    def send_request(self, message_type: str, data: Dict[str, Any] = None, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """发送请求并等待响应"""
        try:
            # 生成唯一的请求ID
            self.request_counter += 1
            request_id = f"req_{self.role}_{self.request_counter}"
            
            # 创建响应队列
            response_queue = Queue()
            self.pending_requests[request_id] = response_queue
            
            # 构造请求消息
            request_data = data or {}
            request_data['request_id'] = request_id
            
            message = IPCMessage(
                msg_type=MessageType(message_type),
                data=request_data,
                sender=self.role
            )
            
            # 发送请求
            client = IPCClient(self.ipc_port)
            if not client.send_message(message):
                logger.error("发送请求消息失败")
                del self.pending_requests[request_id]
                return None
            
            # 等待响应
            try:
                response_data = response_queue.get(timeout=timeout)
                del self.pending_requests[request_id]
                return response_data
            except Empty:
                logger.warning(f"请求超时: {request_id}")
                del self.pending_requests[request_id]
                return None
                
        except Exception as e:
            logger.error(f"发送请求时出错: {e}")
            return None
        
    def send_to_launcher(self, message_type: MessageType, data: Dict[str, Any] = None):
        """向启动器发送消息"""
        message = IPCMessage(message_type, data, self.role)
        client = IPCClient(self.ipc_port)
        return client.send_message(message)
        
    def send_to_updater(self, message_type: MessageType, data: Dict[str, Any] = None):
        """向更新器发送消息"""
        message = IPCMessage(message_type, data, self.role)
        client = IPCClient(self.ipc_port + 1)  # 更新器使用不同端口
        return client.send_message(message)
        
    def send_to_version_api(self, message_type: MessageType, data: Dict[str, Any] = None):
        """向版本API进程发送消息"""
        message = IPCMessage(message_type, data, self.role)
        client = IPCClient(self.ipc_port + 2)  # 版本API使用不同端口
        return client.send_message(message)
        
    def send_heartbeat(self):
        """发送心跳消息"""
        self.send_to_launcher(MessageType.HEARTBEAT, {
            "role": self.role,
            "timestamp": time.time()
        })
        
    def request_shutdown(self):
        """请求关闭"""
        self.send_to_launcher(MessageType.SHUTDOWN_REQUEST, {
            "role": self.role
        })
        
    def notify_update_available(self, version_info: Dict[str, Any]):
        """通知有更新可用"""
        self.send_to_launcher(MessageType.UPDATE_REQUEST, version_info)
        
    def send_response(self, request_id: str, response_data: Dict[str, Any], message_type: MessageType = MessageType.VERSION_INFO):
        """发送响应消息"""
        try:
            response_message = IPCMessage(
                msg_type=message_type,
                data={
                    **response_data,
                    'response_to': request_id
                },
                sender=self.role
            )
            
            client = IPCClient(self.ipc_port)
            return client.send_message(response_message)
        except Exception as e:
            logger.error(f"发送响应消息失败: {e}")
            return False
        
    def shutdown(self):
        """关闭进程管理器"""
        self.server.stop()
        logger.info("进程管理器已关闭")

# 全局进程管理器实例
_process_manager = None

def get_process_manager(role: str = "main") -> ProcessManager:
    """获取全局进程管理器实例"""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager(role)
    return _process_manager

def cleanup_process_manager():
    """清理全局进程管理器"""
    global _process_manager
    if _process_manager:
        _process_manager.shutdown()
        _process_manager = None