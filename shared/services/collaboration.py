"""
实时协作编辑服务

功能：
1. WebSocket 连接管理
2. 文档状态同步
3. 用户 Presence 追踪
4. 操作历史管理
"""
import json
from typing import Dict, Set, Optional, List
from datetime import datetime
from fastapi import WebSocket


class CollaborationService:
    """
    实时协作编辑服务
    
    基于 WebSocket 实现多人实时协作
    """

    def __init__(self):
        # 文档状态 {document_id: content}
        self.document_states: Dict[str, str] = {}

        # WebSocket 连接映射 {document_id: {user_id: websocket}}
        self.document_editors: Dict[str, Dict[str, WebSocket]] = {}

        # 在线用户信息 {document_id: {user_id: user_info}}
        self.online_users: Dict[str, Dict[str, dict]] = {}

        # Awareness 状态 {document_id: {user_id: state}}
        self.awareness_states: Dict[str, Dict[str, dict]] = {}

        # 操作历史 {document_id: [operations]}
        self.operation_history: Dict[str, list] = {}

    async def connect(self, document_id: str, user_id: int, websocket: WebSocket):
        """
        用户连接到文档
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            websocket: WebSocket 连接
        """
        await websocket.accept()

        # 初始化文档编辑器集合
        if document_id not in self.document_editors:
            self.document_editors[document_id] = {}
            self.document_states[document_id] = ""
            self.online_users[document_id] = {}
            self.awareness_states[document_id] = {}
            self.operation_history[document_id] = []

        # 添加编辑器
        self.document_editors[document_id][str(user_id)] = websocket

        # 记录在线用户
        self.online_users[document_id][str(user_id)] = {
            'user_id': user_id,
            'connected_at': datetime.now().isoformat(),
            'cursor_position': 0,
            'name': f'User{user_id}',
        }

        # 初始化 awareness 状态
        self.awareness_states[document_id][str(user_id)] = {
            'user': {
                'id': user_id,
                'name': f'User{user_id}',
                'color': self._get_user_color(user_id),
            },
            'cursor': {'position': 0},
        }

        # 发送当前文档状态
        await websocket.send_json({
            'type': 'init',
            'content': self.document_states.get(document_id, ''),
            'users': list(self.online_users[document_id].keys()),
        })

        # 通知其他用户有新用户加入
        await self._broadcast_presence(document_id, user_id, 'join')

    async def disconnect(self, document_id: str, user_id: int):
        """
        用户断开连接
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
        """
        user_id_str = str(user_id)

        if document_id in self.document_editors:
            # 移除编辑器
            if user_id_str in self.document_editors[document_id]:
                del self.document_editors[document_id][user_id_str]

            # 移除在线用户
            if user_id_str in self.online_users.get(document_id, {}):
                del self.online_users[document_id][user_id_str]

            # 通知其他用户
            await self._broadcast_presence(document_id, user_id, 'leave')

            # 清理空文档
            if not self.document_editors[document_id]:
                del self.document_editors[document_id]
                if document_id in self.document_states:
                    del self.document_states[document_id]
                if document_id in self.online_users:
                    del self.online_users[document_id]
                if document_id in self.operation_history:
                    del self.operation_history[document_id]

    async def handle_operation(self, document_id: str, user_id: int, operation: dict):
        """
        处理编辑操作
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            operation: 操作数据
        """
        op_type = operation.get('type')

        if op_type == 'update_content':
            await self._handle_content_update(document_id, user_id, operation)
        elif op_type == 'cursor_move':
            await self._handle_cursor_move(document_id, user_id, operation)
        elif op_type == 'save':
            await self._handle_save(document_id, user_id)

    async def _handle_content_update(self, document_id: str, user_id: int, operation: dict):
        """
        处理内容更新
        """
        new_content = operation.get('content', '')

        # 更新文档状态
        self.document_states[document_id] = new_content

        # 记录操作历史
        self.operation_history[document_id].append({
            'user_id': user_id,
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
        })

        # 广播给其他用户
        await self._broadcast_to_document(document_id, {
            'type': 'content_update',
            'user_id': user_id,
            'content': new_content,
            'timestamp': datetime.now().isoformat(),
        }, exclude_user=str(user_id))

    async def _handle_cursor_move(self, document_id: str, user_id: int, operation: dict):
        """
        处理光标移动
        """
        position = operation.get('position', 0)

        # 更新用户光标位置
        if document_id in self.online_users:
            user_id_str = str(user_id)
            if user_id_str in self.online_users[document_id]:
                self.online_users[document_id][user_id_str]['cursor_position'] = position

        # 广播光标位置
        await self._broadcast_to_document(document_id, {
            'type': 'cursor_update',
            'user_id': user_id,
            'position': position,
        }, exclude_user=str(user_id))

    async def _handle_save(self, document_id: str, user_id: int):
        """
        处理保存操作
        """
        content = self.document_states.get(document_id, '')

        # 广播保存事件
        await self._broadcast_to_document(document_id, {
            'type': 'saved',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
        })

    async def _broadcast_presence(self, document_id: str, user_id: int, action: str):
        """
        广播用户上下线
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            action: 动作 (join/leave)
        """
        message = {
            'type': 'presence',
            'action': action,
            'user_id': user_id,
            'users': list(self.online_users.get(document_id, {}).keys()),
        }

        await self._broadcast_to_document(document_id, message)

    async def _broadcast_to_document(
            self,
            document_id: str,
            message: dict,
            exclude_user: Optional[str] = None
    ):
        """
        广播消息给文档的所有编辑器
        
        Args:
            document_id: 文档ID
            message: 消息内容
            exclude_user: 排除的用户ID
        """
        if document_id not in self.document_editors:
            return

        disconnected_users = []

        for user_id_str, websocket in self.document_editors[document_id].items():
            if exclude_user and user_id_str == exclude_user:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                # 连接已断开，标记用户
                disconnected_users.append(user_id_str)

        # 清理断开的连接
        for user_id_str in disconnected_users:
            if user_id_str in self.document_editors[document_id]:
                del self.document_editors[document_id][user_id_str]
            if document_id in self.online_users and user_id_str in self.online_users[document_id]:
                del self.online_users[document_id][user_id_str]

    def get_document_state(self, document_id: str) -> str:
        """
        获取文档当前状态
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档内容
        """
        return self.document_states.get(document_id, '')

    def get_online_users(self, document_id: str) -> list:
        """
        获取在线用户列表
        
        Args:
            document_id: 文档ID
            
        Returns:
            在线用户列表
        """
        return list(self.online_users.get(document_id, {}).values())

    def get_active_documents(self) -> list:
        """
        获取有活跃编辑器的文档列表
        
        Returns:
            文档ID列表
        """
        return [
            doc_id for doc_id, editors in self.document_editors.items()
            if len(editors) > 0
        ]

    def _get_user_color(self, user_id: int) -> str:
        """
        为用户生成颜色
        
        Args:
            user_id: 用户ID
            
        Returns:
            颜色代码
        """
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
        ]
        return colors[user_id % len(colors)]

    async def update_awareness(self, document_id: str, user_id: int, state: dict):
        """
        更新 awareness 状态（光标位置、选区等）
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            state: 状态数据
        """
        user_id_str = str(user_id)

        if document_id in self.awareness_states:
            self.awareness_states[document_id][user_id_str] = state

            # 广播 awareness 更新
            await self._broadcast_to_document(document_id, {
                'type': 'awareness',
                'user_id': user_id,
                'state': state,
            }, exclude_user=user_id_str)


# 全局实例
collaboration_service = CollaborationService()
