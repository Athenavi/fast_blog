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
        token: Optional[str] = Query(None, description="JWT Token for authentication"),
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

    # 验证token
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        # TODO: 实现token验证逻辑，这里简化处理
        # 实际应该调用 get_current_user 进行验证
        user_id = 1  # 临时占位，实际需要解析token获取user_id
    except Exception as e:
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
                    # 心跳检测
                    await websocket.send_json({"type": "pong"})

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
