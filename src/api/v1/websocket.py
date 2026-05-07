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

    # TODO: 验证邀请ID是否有效且用户有权限
    # 这里需要查询数据库验证邀请是否存在且未过期

    print(f"[WebSocket] User {user_id} connecting to invite {invite_id}")

    # 接受WebSocket连接
    await websocket.accept()
    print(f"[WebSocket] Connection accepted for user {user_id}")

    # 获取或创建协作文档
    doc = collaboration_service.get_or_create_document(invite_id)

    # 添加客户端
    client_id = f"user_{user_id}"
    doc.add_client(client_id, websocket)
    print(f"[WebSocket] Client {client_id} added to document {invite_id}")

    # 发送当前文档内容
    await websocket.send_json({
        'type': 'init',
        'content': doc.content,
        'version': doc.version,
        'document_id': invite_id
    })

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

                step = Step.from_dict(step_data)
                success = doc.apply_step(step, new_content)

                if success:
                    # 广播给其他客户端
                    await doc.broadcast_step(step, exclude=client_id)

                    # 检查是否需要自动保存
                    if doc.needs_auto_save():
                        print(f"[WebSocket] Auto-save triggered for document {invite_id}")
                        # TODO: 实现自动保存到数据库
            else:
                print(f"[WebSocket] Unknown operation type: {op_type}")

    except WebSocketDisconnect:
        # 用户断开连接
        print(f"[WebSocket] User {user_id} disconnected")
        doc.remove_client(client_id)

    except Exception as e:
        # 其他错误
        print(f"[WebSocket] Error: {e}")
        import traceback
        traceback.print_exc()
        doc.remove_client(client_id)
