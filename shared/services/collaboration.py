"""
实时协作编辑服务

基于WebSocket实现多人实时协作编辑功能
"""
import asyncio
import json
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket


class CollaborativeDocument:
    """协作文档"""

    def __init__(self, document_id: str):
        self.document_id = document_id
        self.clients: Set[WebSocket] = set()
        self.operations: list = []
        self.created_at = datetime.utcnow()
        self.last_modified = datetime.utcnow()
        # 文档内容(简化版,实际应使用Yjs)
        self.content = ""
        self.cursors: Dict[str, dict] = {}  # {client_id: {position, selection}}

    def add_client(self, websocket: WebSocket):
        """添加客户端连接"""
        self.clients.add(websocket)

    def remove_client(self, websocket: WebSocket):
        """移除客户端连接"""
        self.clients.discard(websocket)
        # 清理光标信息
        client_id = id(websocket)
        self.cursors.pop(str(client_id), None)

    async def broadcast(self, message: dict, exclude: Optional[WebSocket] = None):
        """广播消息给所有连接的客户端"""
        disconnected = set()

        for client in self.clients:
            if client != exclude:
                try:
                    await client.send_json(message)
                except Exception as e:
                    print(f"Broadcast error: {e}")
                    disconnected.add(client)

        # 清理断开的连接
        for client in disconnected:
            self.remove_client(client)

    def apply_operation(self, operation: dict, client_id: str):
        """应用操作到文档"""
        op_type = operation.get("type")

        if op_type == "insert":
            position = operation.get("position", 0)
            text = operation.get("text", "")
            self.content = self.content[:position] + text + self.content[position:]

        elif op_type == "delete":
            position = operation.get("position", 0)
            length = operation.get("length", 0)
            self.content = self.content[:position] + self.content[position + length:]

        elif op_type == "replace":
            position = operation.get("position", 0)
            length = operation.get("length", 0)
            text = operation.get("text", "")
            self.content = self.content[:position] + text + self.content[position + length:]

        elif op_type == "cursor":
            # 更新光标位置
            self.cursors[client_id] = {
                "position": operation.get("position", 0),
                "selection": operation.get("selection", None),
                "timestamp": datetime.utcnow().isoformat()
            }
            return  # 光标更新不需要广播内容变更

        self.last_modified = datetime.utcnow()
        self.operations.append({
            "operation": operation,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_state(self) -> dict:
        """获取文档状态"""
        return {
            "document_id": self.document_id,
            "content": self.content,
            "cursors": self.cursors,
            "client_count": len(self.clients),
            "last_modified": self.last_modified.isoformat(),
            "operations_count": len(self.operations)
        }


class CollaborationService:
    """协作服务管理器"""
    
    def __init__(self):
        self.documents: Dict[str, CollaborativeDocument] = {}

    def get_or_create_document(self, document_id: str) -> CollaborativeDocument:
        """获取或创建协作文档"""
        if document_id not in self.documents:
            self.documents[document_id] = CollaborativeDocument(document_id)
        return self.documents[document_id]

    def remove_document(self, document_id: str):
        """删除协作文档"""
        if document_id in self.documents:
            del self.documents[document_id]

    def get_active_documents(self) -> list:
        """获取所有活跃的协作文档"""
        return [
            {
                "document_id": doc.document_id,
                "client_count": len(doc.clients),
                "last_modified": doc.last_modified.isoformat()
            }
            for doc in self.documents.values()
            if len(doc.clients) > 0
        ]
    
    async def connect(self, document_id: str, user_id: int, websocket: WebSocket):
        """连接用户到文档"""
        doc = self.get_or_create_document(document_id)
        doc.add_client(websocket)
        await websocket.send_json({
            "type": "connected",
            "document_id": document_id,
            "user_id": user_id
        })

    async def disconnect(self, document_id: str, user_id: int):
        """断开用户连接"""
        pass
    
    async def handle_operation(self, document_id: str, user_id: int, operation: dict):
        """处理编辑操作"""
        doc = self.get_or_create_document(document_id)
        doc.apply_operation(operation, str(user_id))
        await doc.broadcast({
            "type": "remote_operation",
            "operation": operation,
            "user_id": user_id
        })

    async def update_awareness(self, document_id: str, user_id: int, state: dict):
        """更新用户状态(光标等)"""
        doc = self.get_or_create_document(document_id)
        doc.cursors[str(user_id)] = state


# 全局协作服务实例
collaboration_service = CollaborationService()
