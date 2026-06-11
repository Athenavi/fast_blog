"""
实时协作 WebSocket API
"""
from functools import wraps
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query

from shared.services.chat.collaboration import collaboration_service, Step
from src.api.v2._helpers import ok, fail, _catch
from src.api.v2.collaboration.collaboration_invites import invitations_db
from src.setting import settings

router = APIRouter(tags=["websocket"])


def verify_token_from_cookie(cookie: str) -> Optional[int]:
    """从cookie中验证token并返回user_id"""
    if not cookie:
        print("[WebSocket] No cookie provided")
        return None

    try:
        cookies = cookie.split(';')
        access_token = None
        for c in cookies:
            parts = c.strip().split('=', 1)
            if len(parts) == 2:
                name, value = parts
                if name.strip() == 'access_token':
                    access_token = value.strip()
                    break

        if not access_token:
            print("[WebSocket] No access_token found in cookie")
            return None

        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')
        return user_id
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError as e:
        return None
    except Exception as e:
        return None


@router.websocket("/collaborate/{invite_id}")
async def collaborate_websocket(
        websocket: WebSocket,
        invite_id: str,
        token: Optional[str] = Query(None, description="认证token")
):
    """实时协作编辑 WebSocket"""
    user_id = None

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get('sub') or payload.get('user_id')
            if user_id:
                user_id = int(user_id)
        except Exception:
            pass

    if not user_id:
        await websocket.close(code=4003, reason="Authentication required")
        return

    await websocket.accept()

    invitation = invitations_db.get(invite_id)
    if not invitation:
        await websocket.close(code=4004, reason="Invitation not found")
        return

    from datetime import datetime
    if datetime.now() > invitation["expires_at"]:
        await websocket.close(code=4010, reason="Invitation expired")
        return

    article_id = invitation.get("article_id")
    if not article_id:
        await websocket.close(code=4005, reason="Invalid invitation")
        return

    doc = collaboration_service.get_or_create_document(invite_id)
    doc.article_id = article_id

    if not doc.content:
        try:
            from shared.models.article_content import ArticleContent
            from sqlalchemy import select
            from src.utils.database.unified_manager import db_manager

            async with db_manager.get_session() as db_session:
                content_query = select(ArticleContent).where(ArticleContent.article == article_id)
                result = await db_session.execute(content_query)
                content_obj = result.scalar_one_or_none()
                if content_obj:
                    doc.set_content(content_obj.content)
        except Exception:
            pass

    existing_client_id = None
    for cid in doc.clients.keys():
        if cid.startswith(f"user_{user_id}_"):
            existing_client_id = cid
            break

    if existing_client_id:
        await websocket.close(code=4009, reason="You already have an active collaboration session")
        return

    import uuid
    client_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
    doc.add_client(client_id, websocket)

    await websocket.send_json({
        'type': 'init', 'content': doc.content,
        'version': doc.version, 'document_id': invite_id
    })

    user_list = [
        {'id': cid, 'name': f'User {cid.split("_")[1][:8]}', 'color': '#958DF1'}
        for cid in doc.clients.keys()
    ]

    for cid, client in doc.clients.items():
        try:
            await client.send_json({
                'type': 'user_joined', 'client_id': client_id,
                'client_count': len(doc.clients), 'users': user_list
            })
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_json()
            op_type = data.get('type')

            if op_type == 'awareness':
                doc.awareness[client_id] = data.get('state', {})
                await doc.broadcast_awareness({'clientId': client_id, 'state': data.get('state', {})}, exclude=client_id)
            elif op_type == 'step':
                step_data = data.get('step', {})
                new_content = data.get('content', '')
                step = Step.from_dict(step_data)
                success = doc.apply_step(step, new_content)
                if success:
                    await doc.broadcast_step(step, exclude=client_id)
                    if doc.needs_auto_save():
                        pass
    except WebSocketDisconnect:
        doc.remove_client(client_id)
        user_list = [
            {'id': cid, 'name': f'User {cid.split("_")[1][:8]}', 'color': '#958DF1'}
            for cid in doc.clients.keys()
        ]
        for cid, client in doc.clients.items():
            try:
                await client.send_json({
                    'type': 'user_left', 'client_id': client_id,
                    'client_count': len(doc.clients), 'users': user_list
                })
            except Exception:
                pass
    except Exception as e:
        doc.remove_client(client_id)
        user_list = [
            {'id': cid, 'name': f'User {cid.split("_")[1][:8]}', 'color': '#958DF1'}
            for cid in doc.clients.keys()
        ]
        for cid, client in doc.clients.items():
            try:
                await client.send_json({
                    'type': 'user_left', 'client_id': client_id,
                    'client_count': len(doc.clients), 'users': user_list
                })
            except Exception:
                pass


class ChatGroupManager:
    """群聊 WebSocket 管理器"""

    def __init__(self):
        self.groups: dict[int, dict] = {}

    async def join_group(self, group_id: int, client_id: str, websocket: WebSocket, user_id: int):
        if group_id not in self.groups:
            self.groups[group_id] = {"clients": {}}
        self.groups[group_id]["clients"][client_id] = {"websocket": websocket, "user_id": user_id}
        await self.broadcast_to_group(group_id, {
            'type': 'user_joined', 'user_id': user_id,
            'client_id': client_id, 'online_count': len(self.groups[group_id]["clients"])
        }, exclude=client_id)

    async def leave_group(self, group_id: int, client_id: str):
        if group_id in self.groups and client_id in self.groups[group_id]["clients"]:
            del self.groups[group_id]["clients"][client_id]
            await self.broadcast_to_group(group_id, {
                'type': 'user_left', 'client_id': client_id,
                'online_count': len(self.groups[group_id]["clients"])
            })
            if not self.groups[group_id]["clients"]:
                del self.groups[group_id]

    async def broadcast_to_group(self, group_id: int, message: dict, exclude: str = None):
        if group_id not in self.groups:
            return
        disconnected = []
        for client_id, client_info in self.groups[group_id]["clients"].items():
            if client_id == exclude:
                continue
            try:
                await client_info["websocket"].send_json(message)
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            await self.leave_group(group_id, client_id)

    async def send_message_to_group(self, group_id: int, message_data: dict, sender_id: int):
        await self.broadcast_to_group(group_id, {
            'type': 'new_message', 'message': message_data, 'sender_id': sender_id
        })


chat_group_manager = ChatGroupManager()


@router.websocket("/chat/{group_id}")
async def chat_websocket(
        websocket: WebSocket,
        group_id: int,
        token: Optional[str] = Query(None, description="认证token")
):
    """群聊 WebSocket"""
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get('sub') or payload.get('user_id')
            if user_id:
                user_id = int(user_id)
        except Exception:
            pass

    if not user_id:
        await websocket.close(code=4003, reason="Authentication required")
        return

    try:
        from shared.models.chat_group_member import ChatGroupMember
        from sqlalchemy import select
        from src.utils.database.unified_manager import db_manager

        async with db_manager.get_session() as db_session:
            stmt = select(ChatGroupMember).where(
                (ChatGroupMember.group == group_id) & (ChatGroupMember.user == user_id)
            )
            result = await db_session.execute(stmt)
            member = result.scalar_one_or_none()
            if not member:
                await websocket.close(code=4003, reason="Not a member of this group")
                return
    except Exception:
        await websocket.close(code=500, reason="Internal error")
        return

    await websocket.accept()
    import uuid
    client_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
    await chat_group_manager.join_group(group_id, client_id, websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            op_type = data.get('type')

            if op_type == 'send_message':
                content = data.get('content', '')
                message_type = data.get('message_type', 'text')
                attachment_url = data.get('attachment_url')
                parent_message = data.get('parent_message')

                if not content:
                    await websocket.send_json({'type': 'error', 'message': 'Content is required'})
                    continue

                try:
                    from shared.models.private_message import PrivateMessage
                    from datetime import datetime
                    from sqlalchemy import update
                    from src.utils.database.unified_manager import db_manager

                    async with db_manager.get_session() as db_session:
                        new_message = PrivateMessage(
                            sender=user_id, recipient=None, group=group_id,
                            content=content, message_type=message_type,
                            attachment_url=attachment_url, parent_message=parent_message,
                            created_at=datetime.now(), updated_at=datetime.now()
                        )
                        db_session.add(new_message)
                        await db_session.commit()
                        await db_session.refresh(new_message)
                        message_data = new_message.to_dict()

                        from shared.models.chat_group import ChatGroup
                        update_stmt = (
                            update(ChatGroup).where(ChatGroup.id == group_id)
                            .values(last_message_at=datetime.now(), updated_at=datetime.now())
                        )
                        await db_session.execute(update_stmt)
                        await db_session.commit()

                    await chat_group_manager.send_message_to_group(group_id, message_data, user_id)
                except Exception:
                    await websocket.send_json({'type': 'error', 'message': 'Failed to send message'})

            elif op_type == 'typing':
                await chat_group_manager.broadcast_to_group(
                    group_id, {'type': 'user_typing', 'user_id': user_id, 'client_id': client_id},
                    exclude=client_id
                )

            elif op_type == 'read':
                message_ids = data.get('message_ids', [])
                if message_ids:
                    try:
                        from shared.models.private_message import PrivateMessage
                        from datetime import datetime
                        from sqlalchemy import update
                        from src.utils.database.unified_manager import db_manager

                        async with db_manager.get_session() as db_session:
                            update_stmt = (
                                update(PrivateMessage).where(PrivateMessage.id.in_(message_ids))
                                .values(is_read=True, read_at=datetime.now())
                            )
                            await db_session.execute(update_stmt)
                            await db_session.commit()
                    except Exception:
                        pass
    except WebSocketDisconnect:
        await chat_group_manager.leave_group(group_id, client_id)
    except Exception:
        await chat_group_manager.leave_group(group_id, client_id)
