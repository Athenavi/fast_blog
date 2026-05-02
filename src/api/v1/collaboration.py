"""
实时协作编辑 WebSocket API

提供基于 ProseMirror collab 协议的实时协作编辑功能
"""
import json
from typing import Optional

try:
    from shared.services.collaboration import collaboration_service, Step

    COLLAB_AVAILABLE = True
except ImportError:
    COLLAB_AVAILABLE = False
    collaboration_service = None
    Step = None
    print("Warning: Collaboration service not available")

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.utils.database.main import get_async_session

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


@router.websocket("/ws/{document_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        document_id: str,
        client_id: Optional[str] = Query(None, description="Client identifier"),
        article_id: Optional[int] = Query(None, description="Article ID")
):
    """
    WebSocket 协作文档端点 - 基于 ProseMirror collab 协议
    
    支持的操作类型:
    - send_steps: 发送编辑步骤
    - receive_steps: 接收编辑步骤（服务器推送）
    - awareness: 用户感知状态（光标、选区等）
    - ping: 心跳检测
    """
    print(f"\n{'=' * 60}")
    print(f"[Collaboration Debug] WebSocket connection attempt")
    print(f"[Collaboration Debug] Document ID: {document_id}")
    print(f"[Collaboration Debug] Article ID: {article_id}")
    print(f"[Collaboration Debug] Client ID: {client_id}")

    # 打印 WebSocket scope 信息
    print(f"[Collaboration Debug] WebSocket scope keys: {list(websocket.scope.keys())}")

    # 从 WebSocket headers 中提取 token 进行认证
    from src.extensions import get_async_db_session
    import jwt as pyjwt
    from sqlalchemy import select
    from shared.models.user import User as UserModel

    print(f"[Collaboration Debug] Attempting authentication...")
    print(f"[Collaboration Debug] WebSocket scope keys: {list(websocket.scope.keys())}")

    # 打印所有 headers
    headers_list = websocket.scope.get("headers", [])
    print(f"[Collaboration Debug] Headers count: {len(headers_list)}")

    # 提取 token：优先从 Authorization header，其次从 cookie
    token = None
    cookies_dict = {}

    for name, value in headers_list:
        header_name = name.decode("utf-8") if isinstance(name, bytes) else name
        header_value = value.decode("utf-8") if isinstance(value, bytes) else value

        # 检查 Authorization header
        if header_name.lower() == "authorization" and header_value.startswith("Bearer "):
            token = header_value[len("Bearer "):]
            print(f"[Collaboration Debug] Token found in Authorization header")

        # 收集 cookies
        if header_name.lower() == "cookie":
            print(f"[Collaboration Debug] Cookie header: {header_value[:200]}...")
            # 解析 cookie 字符串: "key1=value1; key2=value2"
            for item in header_value.split(";"):
                if "=" in item:
                    key, val = item.strip().split("=", 1)
                    cookies_dict[key] = val

    # 如果 Authorization header 中没有 token，尝试从 cookie 获取
    if not token:
        token = cookies_dict.get("access_token") or cookies_dict.get("access_token_cookie")
        if token:
            print(f"[Collaboration Debug] Token found in cookie")
    
    try:
        if not token:
            print(f"[Collaboration Debug] ✗ No token found in request")
            print(f"[Collaboration Debug] Available cookies: {list(cookies_dict.keys())}")
            print(f"{'=' * 60}\n")
            await websocket.accept()
            await websocket.close(code=4001, reason="Authentication failed: No token provided")
            return

        print(f"[Collaboration Debug] Token found: {token[:20]}...")

        # 验证 JWT token
        from src.setting import settings
        jwt_secret = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        jwt_algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

        payload = pyjwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        user_id_str = payload.get("sub")

        if not user_id_str:
            print(f"[Collaboration Debug] ✗ Invalid token: missing subject")
            print(f"{'=' * 60}\n")
            await websocket.accept()
            await websocket.close(code=4001, reason="Authentication failed: Invalid token")
            return

        user_id = int(user_id_str)
        print(f"[Collaboration Debug] User ID from token: {user_id}")

        # 从数据库加载用户 - 使用 async for 正确处理异步生成器
        async for db_session in get_async_db_session():
            result = await db_session.execute(select(UserModel).where(UserModel.id == user_id))
            current_user = result.scalar_one_or_none()

            if not current_user or not current_user.is_active:
                print(f"[Collaboration Debug] ✗ User not found or inactive: {user_id}")
                print(f"{'=' * 60}\n")
                await websocket.accept()
                await websocket.close(code=4001, reason="Authentication failed: User not found or inactive")
                return

            print(f"[Collaboration] ✓ User {user_id} ({current_user.username}) authenticated successfully")
            print(f"{'=' * 60}\n")
        
    except Exception as e:
        print(f"[Collaboration Debug] ✗ Authentication failed!")
        print(f"[Collaboration Debug] Error type: {type(e).__name__}")
        print(f"[Collaboration Debug] Error message: {str(e)}")
        import traceback
        print(f"[Collaboration Debug] Traceback:")
        traceback.print_exc()
        print(f"{'=' * 60}\n")
        # WebSocket 认证失败，先 accept 再关闭
        await websocket.accept()
        await websocket.close(code=4001, reason=f"Authentication failed: {str(e)}")
        return

    await websocket.accept()

    # 生成客户端ID
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())

    # 获取或创建协作文档
    doc = collaboration_service.get_or_create_document(document_id, article_id)

    # 如果文档内容为空且有 article_id，从数据库加载文章内容
    if not doc.get_content() and article_id:
        print(f"[Collab] Document content is empty, loading from article {article_id}...")
        try:
            from shared.models.article import Article
            from shared.models.article_content import ArticleContent
            from sqlalchemy import select

            async for db_session in get_async_db_session():
                # 查询文章内容
                content_query = select(ArticleContent).where(
                    ArticleContent.article == article_id
                )
                result = await db_session.execute(content_query)
                content_obj = result.scalar_one_or_none()

                if content_obj and content_obj.content:
                    doc.set_content(content_obj.content)
                    print(f"[Collab] ✓ Loaded content from article {article_id}, length: {len(content_obj.content)}")
                else:
                    print(f"[Collab] ⚠ No content found for article {article_id}")
                break
        except Exception as e:
            print(f"[Collab] ✗ Error loading article content: {e}")
            import traceback
            traceback.print_exc()

    # 添加客户端
    doc.add_client(client_id, websocket)

    # 发送欢迎消息和当前文档状态
    content_to_send = doc.get_content()
    print(f"[Collab] Sending welcome message with content length: {len(content_to_send)}")
    if content_to_send:
        print(f"[Collab] Content preview: {content_to_send[:100]}...")
    
    await websocket.send_json({
        "type": "welcome",
        "document_id": document_id,
        "client_id": client_id,
        "article_id": doc.article_id,
        "version": doc.version,
        "content": content_to_send,
        "state": doc.get_state()
    })
    print(f"[Collab] ✓ Welcome message sent")

    # 通知其他客户端有新用户加入
    await doc.broadcast_awareness({
        "type": "user_joined",
        "client_id": client_id,
        "client_count": len(doc.clients)
    }, exclude=client_id)

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                # 处理JSON消息
                message = json.loads(data["text"])
                msg_type = message.get("type")

                if msg_type == "send_steps":
                    # 处理编辑步骤
                    steps_data = message.get("steps", [])
                    new_content = message.get("content", "")

                    for step_data in steps_data:
                        step = Step.from_dict(step_data)
                        # 应用步骤到文档
                        doc.apply_step(step, new_content)
                        # 广播给其他客户端
                        await doc.broadcast_step(step, exclude=client_id)

                    print(f"[Collab] Received {len(steps_data)} steps from client {client_id}")

                elif msg_type == "awareness":
                    # 处理感知状态更新（光标、选区等）
                    awareness_state = message.get("state", {})
                    doc.awareness[client_id] = {
                        **awareness_state,
                        "client_id": client_id,
                        "timestamp": doc.last_modified.isoformat()
                    }

                    # 广播感知状态
                    await doc.broadcast_awareness({
                        "type": "awareness",
                        "client_id": client_id,
                        "state": doc.awareness[client_id]
                    }, exclude=client_id)

                elif msg_type == "ping":
                    # 心跳检测，同时检查是否需要自动保存
                    await websocket.send_json({"type": "pong"})

                    # 检查是否需要自动保存
                    doc_obj = collaboration_service.documents.get(document_id)
                    if doc_obj and doc_obj.needs_auto_save() and len(doc_obj.clients) > 0:
                        print(f"[Auto-save] Triggering auto-save for document {document_id}")
                        async for db_session in get_async_db_session():
                            success = await collaboration_service.save_to_revision(
                                document_id=document_id,
                                db_session=db_session,
                                author_id=user_id,
                                change_summary="自动保存"
                            )
                            if success:
                                await websocket.send_json({
                                    "type": "auto_save",
                                    "success": True,
                                    "message": "文档已自动保存"
                                })

                elif msg_type == "save":
                    # 手动保存到修订版本
                    async for db_session in get_async_db_session():
                        success = await collaboration_service.save_to_revision(
                            document_id=document_id,
                            db_session=db_session,
                            author_id=user_id,
                            change_summary=message.get("change_summary", "协作编辑保存")
                        )
                        await websocket.send_json({
                            "type": "save_result",
                            "success": success
                        })

    except WebSocketDisconnect:
        # 客户端断开连接
        doc.remove_client(client_id)

        # 通知其他客户端
        await doc.broadcast_awareness({
            "type": "user_left",
            "client_id": client_id,
            "client_count": len(doc.clients)
        })

        # 如果没有客户端了,清理文档
        if len(doc.clients) == 0:
            collaboration_service.remove_document(document_id)

    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        doc.remove_client(client_id)
        await doc.broadcast_awareness({
            "type": "user_left",
            "client_id": client_id,
            "client_count": len(doc.clients)
        })


@router.get("/documents")
async def list_active_documents():
    """
    获取所有活跃的协作文档列表
    """
    documents = collaboration_service.get_active_documents()
    return {
        "success": True,
        "data": {
            "documents": documents,
            "count": len(documents)
        }
    }


@router.get("/document/{document_id}/state")
async def get_document_state(
        document_id: str,
        current_user=Depends(get_current_user)
):
    """
    获取指定文档的状态(非WebSocket方式)
    需要登录访问
    """
    doc = collaboration_service.documents.get(document_id)

    if not doc:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Document not found"}
        )

    return {
        "success": True,
        "data": doc.get_state()
    }


@router.post("/document/{document_id}/save")
async def save_document(
        document_id: str,
        save_data: dict,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session)
):
    """
    保存协作文档内容到文章修订版本
    
    Args:
        document_id: 文档ID
        save_data: {"content": "...", "change_summary": "..."}
    """
    doc = collaboration_service.documents.get(document_id)

    if not doc:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Document not found"}
        )

    # 如果提供了新内容，先更新文档
    if "content" in save_data:
        doc.set_content(save_data["content"])

    # 保存到修订版本
    change_summary = save_data.get("change_summary", "协作编辑保存")
    success = await collaboration_service.save_to_revision(
        document_id=document_id,
        db_session=db,
        author_id=current_user.id,
        change_summary=change_summary
    )

    if not success:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to save to revision"}
        )

    return {
        "success": True,
        "message": "Document saved successfully to revision",
        "data": {
            "document_id": document_id,
            "article_id": doc.article_id,
            "content_length": len(doc.get_content()),
            "saved_at": doc.last_modified.isoformat()
        }
    }
