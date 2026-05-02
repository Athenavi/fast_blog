"""
实时协作编辑服务

基于Yjs CRDT实现多人实时协作编辑功能
"""
from datetime import datetime
from typing import Dict, Optional

import y_py as Y
from fastapi import WebSocket


class CollaborativeDocument:
    """协作文档 - 基于Yjs CRDT"""

    def __init__(self, document_id: str):
        self.document_id = document_id
        self.clients: Dict[str, WebSocket] = {}  # {client_id: websocket}
        self.created_at = datetime.utcnow()
        self.last_modified = datetime.utcnow()
        # Yjs文档
        self.ydoc = Y.YDoc()
        self.ytext = self.ydoc.get_text('content')
        # 用户感知状态
        self.awareness: Dict[str, dict] = {}
        self.article_id: Optional[int] = None  # 关联的文章ID

    def add_client(self, client_id: str, websocket: WebSocket):
        """添加客户端连接"""
        self.clients[client_id] = websocket

    def remove_client(self, client_id: str):
        """移除客户端连接"""
        if client_id in self.clients:
            del self.clients[client_id]
        # 清理光标信息
        self.awareness.pop(client_id, None)

    async def broadcast_update(self, update: bytes, exclude: Optional[str] = None):
        """广播Yjs更新给所有连接的客户端"""
        disconnected = []

        for client_id, client in self.clients.items():
            if client_id != exclude:
                try:
                    await client.send_bytes(update)
                except Exception as e:
                    print(f"Broadcast error for client {client_id}: {e}")
                    disconnected.append(client_id)

        # 清理断开的连接
        for client_id in disconnected:
            self.remove_client(client_id)

    async def broadcast_awareness(self, awareness_state: dict, exclude: Optional[str] = None):
        """广播感知状态（光标等）"""
        disconnected = []

        for client_id, client in self.clients.items():
            if client_id != exclude:
                try:
                    await client.send_json({
                        'type': 'awareness',
                        'state': awareness_state
                    })
                except Exception as e:
                    print(f"Awareness broadcast error for client {client_id}: {e}")
                    disconnected.append(client_id)

        # 清理断开的连接
        for client_id in disconnected:
            self.remove_client(client_id)

    def apply_yjs_update(self, update: bytes, client_id: str):
        """应用Yjs更新到文档"""
        try:
            Y.apply_update(self.ydoc, update)
            self.last_modified = datetime.utcnow()
            return True
        except Exception as e:
            print(f"Error applying Yjs update: {e}")
            return False

    def get_content(self) -> str:
        """获取文档内容"""
        return str(self.ytext)

    def set_content(self, content: str):
        """设置文档内容"""
        self.ytext.delete(0, len(self.ytext))
        self.ytext.insert(0, content)
        self.last_modified = datetime.utcnow()

    def get_state(self) -> dict:
        """获取文档状态"""
        return {
            "document_id": self.document_id,
            "content": self.get_content(),
            "article_id": self.article_id,
            "awareness": self.awareness,
            "client_count": len(self.clients),
            "last_modified": self.last_modified.isoformat()
        }

    def get_yjs_state_vector(self) -> bytes:
        """获取Yjs状态向量用于增量同步"""
        return Y.encode_state_vector(self.ydoc)

    def get_yjs_full_state(self) -> bytes:
        """获取完整的Yjs文档状态"""
        return Y.encode_state_as_update(self.ydoc)


class CollaborationService:
    """协作服务管理器"""
    
    def __init__(self):
        self.documents: Dict[str, CollaborativeDocument] = {}

    def get_or_create_document(self, document_id: str, article_id: Optional[int] = None) -> CollaborativeDocument:
        """获取或创建协作文档"""
        if document_id not in self.documents:
            doc = CollaborativeDocument(document_id)
            if article_id:
                doc.article_id = article_id
            self.documents[document_id] = doc
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
                "article_id": doc.article_id,
                "client_count": len(doc.clients),
                "last_modified": doc.last_modified.isoformat()
            }
            for doc in self.documents.values()
            if len(doc.clients) > 0
        ]

    async def save_to_revision(self, document_id: str, db_session, author_id: int,
                               change_summary: str = "协作编辑保存"):
        """将协作文档保存到文章修订版本"""
        from shared.services.article_manager import save_article_revision

        doc = self.documents.get(document_id)
        if not doc or not doc.article_id:
            return False

        try:
            # 使用现有的修订服务保存
            revision = await save_article_revision(
                db=db_session,
                article_id=doc.article_id,
                author_id=author_id,
                change_summary=change_summary
            )
            return revision is not None
        except Exception as e:
            print(f"Error saving to revision: {e}")
            return False


# 全局协作服务实例
collaboration_service = CollaborationService()
