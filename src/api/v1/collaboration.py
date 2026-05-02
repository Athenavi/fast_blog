"""
实时协作编辑 WebSocket API

提供基于Yjs CRDT的实时协作编辑功能
"""
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.collaboration import collaboration_service
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
    WebSocket 协作文档端点 - 基于Yjs CRDT
    
    支持的操作类型:
    - yjs-sync: Yjs初始同步
    - yjs-update: Yjs增量更新
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

    # 从 WebSocket headers 中提取 cookie 进行认证
    from src.auth.auth_deps import _authenticate_user
    from src.extensions import get_async_db_session
    from starlette.requests import HTTPConnection

    # 创建 Mock Request 对象，需要从 WebSocket scope 中提取 cookies
    # WebSocket 的 cookies 在 headers 中的 'cookie' 字段
    cookies = {}
    cookie_header = websocket.scope.get("headers", [])
    print(f"[Collaboration Debug] Headers count: {len(cookie_header)}")

    for name, value in cookie_header:
        header_name = name.decode("utf-8") if isinstance(name, bytes) else name
        if header_name.lower() == "cookie":
            cookie_str = value.decode("utf-8") if isinstance(value, bytes) else value
            print(f"[Collaboration Debug] Raw cookie string: {cookie_str[:100]}...")
            # 解析 cookie 字符串: "key1=value1; key2=value2"
            for item in cookie_str.split(";"):
                if "=" in item:
                    key, val = item.strip().split("=", 1)
                    cookies[key] = val
            break

    print(f"[Collaboration Debug] Extracted cookies: {list(cookies.keys())}")
    print(f"[Collaboration Debug] Has access_token: {'access_token' in cookies}")

    # 创建带有 cookies 的 mock request
    mock_request = HTTPConnection(scope=websocket.scope)
    mock_request._cookies = cookies  # 直接设置 cookies

    # 获取数据库会话
    db_session = get_async_db_session()
    
    try:
        print(f"[Collaboration Debug] Attempting authentication...")
        # 使用系统的认证函数
        current_user = await _authenticate_user(mock_request, db_session, required=True)
        user_id = current_user.id
        print(f"[Collaboration] ✓ User {user_id} authenticated successfully from cookie")
        print(f"{'=' * 60}\n")
    except Exception as e:
        print(f"[Collaboration Debug] ✗ Authentication failed!")
        print(f"[Collaboration Debug] Error type: {type(e).__name__}")
        print(f"[Collaboration Debug] Error message: {str(e)}")
        import traceback
        print(f"[Collaboration Debug] Traceback:")
        traceback.print_exc()
        print(f"{'=' * 60}\n")
        await websocket.close(code=4001, reason=f"Authentication failed: {str(e)}")
        return

    await websocket.accept()

    # 生成客户端ID
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())

    # 获取或创建协作文档
    doc = collaboration_service.get_or_create_document(document_id, article_id)

    # 添加客户端
    doc.add_client(client_id, websocket)

    # 发送欢迎消息和当前文档状态
    initial_state = doc.get_yjs_full_state()
    await websocket.send_bytes(initial_state)
    
    await websocket.send_json({
        "type": "welcome",
        "document_id": document_id,
        "client_id": client_id,
        "article_id": doc.article_id,
        "state": doc.get_state()
    })

    # 通知其他客户端有新用户加入
    await doc.broadcast_awareness({
        "type": "user_joined",
        "client_id": client_id,
        "client_count": len(doc.clients)
    }, exclude=client_id)

    try:
        while True:
            # 接收消息（可能是二进制Yjs更新或JSON消息）
            data = await websocket.receive()

            if "bytes" in data:
                # 处理Yjs二进制更新
                update_bytes = data["bytes"]
                if doc.apply_yjs_update(update_bytes, client_id):
                    # 广播给其他客户端
                    await doc.broadcast_update(update_bytes, exclude=client_id)

            elif "text" in data:
                # 处理JSON消息
                message = json.loads(data["text"])
                msg_type = message.get("type")

                if msg_type == "awareness":
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
                        from src.extensions import get_async_db_session
                        db_session = get_async_db_session()
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
                    from src.extensions import get_async_db_session
                    db_session = get_async_db_session()
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
