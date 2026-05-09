"""
实时协作 WebSocket API
"""
from typing import Optional

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from shared.services.collaboration import collaboration_service, Step
from src.setting import settings

router = APIRouter(prefix="/ws", tags=["websocket"])


def verify_token_from_cookie(cookie: str) -> Optional[int]:
    """从cookie中验证token并返回user_id"""
    if not cookie:
        print("[WebSocket] No cookie provided")
        return None

    try:
        # 解析cookie获取access_token
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
            print(f"[WebSocket] Cookie content: {cookie}")
            return None

        print(f"[WebSocket] Found access_token: {access_token[:20]}...")

        # 解码JWT token
        payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get('user_id')
        print(f"[WebSocket] Token verified, user_id: {user_id}")
        return user_id
    except jwt.ExpiredSignatureError:
        print("[WebSocket] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[WebSocket] Invalid token: {e}")
        return None
    except Exception as e:
        print(f"[WebSocket] Token verification failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


@router.websocket("/collaborate/{invite_id}")
async def collaborate_websocket(
        websocket: WebSocket,
        invite_id: str,
        token: Optional[str] = Query(None, description="认证token")
):
    """
    实时协作编辑 WebSocket
    
    Args:
        websocket: WebSocket 连接
        invite_id: 邀请ID（UUID）
        token: 认证token（通过URL参数传递）
    """
    # 验证用户身份
    user_id = None

    if token:
        try:
            # 解码JWT token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            # JWT token中使用'sub'字段存储user_id
            user_id = payload.get('sub') or payload.get('user_id')
            if user_id:
                user_id = int(user_id)  # 确保是整数
            print(f"[WebSocket] Token verified from URL param, payload: {payload}, user_id: {user_id}")
        except jwt.ExpiredSignatureError:
            print("[WebSocket] Token expired")
        except jwt.InvalidTokenError as e:
            print(f"[WebSocket] Invalid token: {e}")
        except Exception as e:
            print(f"[WebSocket] Token verification failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[WebSocket] No token provided in URL")

    if not user_id:
        # 认证失败，关闭连接
        await websocket.close(code=4003, reason="Authentication required")
        return

    print(f"[WebSocket] User {user_id} connecting to invite {invite_id}")

    # 接受WebSocket连接（必须先accept才能发送消息）
    await websocket.accept()
    print(f"[WebSocket] Connection accepted for user {user_id}")

    # 从邀请记录中获取 article_id
    from src.api.v1.collaboration_invites import invitations_db
    invitation = invitations_db.get(invite_id)

    if not invitation:
        print(f"[WebSocket] Invitation {invite_id} not found")
        await websocket.close(code=4004, reason="Invitation not found")
        return

    # 检查邀请是否过期
    from datetime import datetime
    if datetime.now() > invitation["expires_at"]:
        print(f"[WebSocket] Invitation {invite_id} expired")
        await websocket.close(code=4010, reason="Invitation expired")
        return

    article_id = invitation.get("article_id")
    if not article_id:
        print(f"[WebSocket] No article_id in invitation {invite_id}")
        await websocket.close(code=4005, reason="Invalid invitation")
        return

    print(f"[WebSocket] Invite {invite_id} maps to article {article_id}")

    # 获取或创建协作文档（使用invite_id作为文档ID）
    doc = collaboration_service.get_or_create_document(invite_id)
    doc.article_id = article_id  # 设置文章ID

    # 如果是新创建的文档，从数据库加载初始内容
    if not doc.content:
        try:
            from shared.models.article_content import ArticleContent
            from sqlalchemy import select
            from src.utils.database.unified_manager import db_manager

            async with db_manager.get_session() as db_session:
                content_query = select(ArticleContent).where(
                    ArticleContent.article == article_id
                )
                result = await db_session.execute(content_query)
                content_obj = result.scalar_one_or_none()

                if content_obj:
                    doc.set_content(content_obj.content)
                    print(f"[WebSocket] Loaded initial content for article {article_id}")
                else:
                    print(f"[WebSocket] No content found for article {article_id}")
        except Exception as e:
            print(f"[WebSocket] Failed to load initial content: {e}")
            import traceback
            traceback.print_exc()

    # 检查用户是否已有活跃连接
    existing_client_id = None
    for cid in doc.clients.keys():
        if cid.startswith(f"user_{user_id}_"):
            existing_client_id = cid
            break

    if existing_client_id:
        print(f"[WebSocket] User {user_id} already has an active connection: {existing_client_id}")
        await websocket.close(code=4009, reason="You already have an active collaboration session")
        return

    # 添加客户端 - 使用唯一ID标识此连接
    import uuid
    client_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
    doc.add_client(client_id, websocket)
    print(
        f"[WebSocket] Client {client_id} (user_id={user_id}) added to document {invite_id}, total clients: {len(doc.clients)}")

    # 发送当前文档内容
    print(f"[WebSocket] Sending init message, content length: {len(doc.content)}, version: {doc.version}")
    if doc.content:
        print(f"[WebSocket] Content preview: {doc.content[:100]}")
    else:
        print(f"[WebSocket] WARNING: Document content is empty!")

    await websocket.send_json({
        'type': 'init',
        'content': doc.content,
        'version': doc.version,
        'document_id': invite_id
    })

    # 广播用户加入消息，包含用户列表
    user_list = [
        {
            'id': cid,
            'name': f'User {cid.split("_")[1][:8]}',  # 从 client_id 提取用户ID
            'color': '#958DF1'  # 默认颜色
        }
        for cid in doc.clients.keys()
    ]

    print(f"[WebSocket] Broadcasting user_joined to {len(doc.clients)} clients")
    print(f"[WebSocket] User list: {user_list}")

    # 直接向所有客户端发送用户列表更新
    for cid, client in doc.clients.items():
        try:
            await client.send_json({
                'type': 'user_joined',
                'client_id': client_id,
                'client_count': len(doc.clients),
                'users': user_list
            })
            print(f"[WebSocket] Sent user_joined to {cid}")
        except Exception as e:
            print(f"Error broadcasting to {cid}: {e}")

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            # 处理操作
            op_type = data.get('type')

            if op_type == 'awareness':
                # 处理 awareness 更新
                doc.awareness[client_id] = data.get('state', {})
                await doc.broadcast_awareness({
                    'clientId': client_id,
                    'state': data.get('state', {})
                }, exclude=client_id)
            elif op_type == 'step':
                # 处理编辑步骤
                step_data = data.get('step', {})
                new_content = data.get('content', '')

                print(f"[WebSocket] Received step from {client_id}, content length: {len(new_content)}")

                step = Step.from_dict(step_data)
                success = doc.apply_step(step, new_content)

                if success:
                    print(f"[WebSocket] Step applied successfully, broadcasting to other clients...")
                    print(f"[WebSocket] Document has {len(doc.clients)} clients total")
                    # 广播给其他客户端
                    await doc.broadcast_step(step, exclude=client_id)
                    print(f"[WebSocket] Broadcast completed")

                    # 检查是否需要自动保存
                    if doc.needs_auto_save():
                        print(f"[WebSocket] Auto-save triggered for document {invite_id}")
                        # TODO: 实现自动保存到数据库
                else:
                    print(f"[WebSocket] Failed to apply step")
            else:
                print(f"[WebSocket] Unknown operation type: {op_type}")

    except WebSocketDisconnect:
        # 用户断开连接
        print(f"[WebSocket] User {user_id} disconnected")
        doc.remove_client(client_id)

        # 广播用户离开消息，包含更新后的用户列表
        user_list = [
            {
                'id': cid,
                'name': f'User {cid.split("_")[1][:8]}',
                'color': '#958DF1'
            }
            for cid in doc.clients.keys()
        ]

        # 直接向所有客户端发送用户列表更新
        for cid, client in doc.clients.items():
            try:
                await client.send_json({
                    'type': 'user_left',
                    'client_id': client_id,
                    'client_count': len(doc.clients),
                    'users': user_list
                })
            except Exception as e:
                print(f"Error broadcasting to {cid}: {e}")

    except Exception as e:
        # 其他错误
        print(f"[WebSocket] Error: {e}")
        import traceback
        traceback.print_exc()
        doc.remove_client(client_id)

        # 广播用户离开消息
        user_list = [
            {
                'id': cid,
                'name': f'User {cid.split("_")[1][:8]}',
                'color': '#958DF1'
            }
            for cid in doc.clients.keys()
        ]

        # 直接向所有客户端发送用户列表更新
        for cid, client in doc.clients.items():
            try:
                await client.send_json({
                    'type': 'user_left',
                    'client_id': client_id,
                    'client_count': len(doc.clients),
                    'users': user_list
                })
            except Exception as e:
                print(f"Error broadcasting to {cid}: {e}")
