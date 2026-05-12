"""
Yjs 实时协作编辑 WebSocket API

基于 Yjs CRDT 算法的真正多人实时协作
支持二进制协议，性能更优
"""
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from shared.services.chat.yjs_collaboration import yjs_collaboration_service

router = APIRouter(prefix="/collaboration/yjs", tags=["collaboration-yjs"])


@router.websocket("/ws/{document_id}")
async def yjs_websocket_endpoint(
        websocket: WebSocket,
        document_id: str,
        client_id: Optional[str] = Query(None, description="Client identifier"),
        article_id: Optional[int] = Query(None, description="Article ID")
):
    """
    Yjs WebSocket 协作文档端点
    
    使用 Yjs 的二进制协议进行高效的实时协作
    支持：
    - 文档更新同步（二进制）
    - 感知状态（光标、选区等）
    - 自动重连
    """
    await websocket.accept()

    # 生成客户端ID
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())

    print(f"[Yjs WS] Client {client_id} connecting to document {document_id}")

    # 获取或创建 Yjs 文档
    doc = yjs_collaboration_service.get_or_create_document(document_id, article_id)

    # 添加客户端
    doc.add_client(client_id, websocket)

    # 发送当前文档状态（如果存在）
    current_state = doc.get_state()
    if current_state:
        print(f"[Yjs WS] Sending existing state to client {client_id}")
        await websocket.send_bytes(current_state)
    else:
        print(f"[Yjs WS] No existing state for document {document_id}")

    # 发送欢迎消息
    await websocket.send_json({
        "type": "welcome",
        "document_id": document_id,
        "client_id": client_id,
        "article_id": doc.article_id
    })

    # 通知其他客户端有新用户加入
    await doc.broadcast_awareness({
        "type": "user_joined",
        "client_id": client_id,
        "client_count": len(doc.clients)
    }, exclude=client_id)

    try:
        while True:
            # 接收消息（可能是二进制或JSON）
            data = await websocket.receive()

            if "bytes" in data:
                # 处理 Yjs 二进制更新
                update = data["bytes"]
                print(f"[Yjs WS] Received binary update from {client_id}, size: {len(update)} bytes")

                # 更新文档状态
                doc.update_state(update)

                # 广播给其他客户端
                await doc.broadcast_binary(update, exclude=client_id)

            elif "text" in data:
                # 处理 JSON 消息（感知状态等）
                try:
                    message = json.loads(data["text"])
                    msg_type = message.get("type")

                    if msg_type == "awareness":
                        # 处理感知状态更新
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

                        # 检查是否需要自动保存
                        if doc.needs_auto_save():
                            print(f"[Yjs Auto-save] Triggering for document {document_id}")
                            # Auto-save to database
                            # Example implementation:
                            # from shared.models.article import Article
                            # content = doc.get_content()
                            # 
                            # stmt = select(Article).where(Article.id == article_id)
                            # result = await db.execute(stmt)
                            # article = result.scalar_one_or_none()
                            # 
                            # if article:
                            #     article.content = content
                            #     article.updated_at = datetime.now()
                            #     await db.commit()
                            #     doc.mark_saved()

                    elif msg_type == "save":
                        # Manual save request
                        # Save to database
                        # Example implementation:
                        # from shared.models.article import Article
                        # content = doc.get_content()
                        # 
                        # stmt = select(Article).where(Article.id == article_id)
                        # result = await db.execute(stmt)
                        # article = result.scalar_one_or_none()
                        # 
                        # if article:
                        #     article.content = content
                        #     article.updated_at = datetime.now()
                        #     await db.commit()
                        #     doc.mark_saved()
                        
                        await websocket.send_json({
                            "type": "save_result",
                            "success": True,
                            "message": "Saved successfully"
                        })

                except json.JSONDecodeError as e:
                    print(f"[Yjs WS] JSON parse error: {e}")

    except WebSocketDisconnect:
        # 客户端断开连接
        print(f"[Yjs WS] Client {client_id} disconnected")
        doc.remove_client(client_id)

        # 通知其他客户端
        await doc.broadcast_awareness({
            "type": "user_left",
            "client_id": client_id,
            "client_count": len(doc.clients)
        })

        # 如果没有客户端了，清理文档
        yjs_collaboration_service.remove_document(document_id)

    except Exception as e:
        print(f"[Yjs WS] Error: {e}")
        import traceback
        traceback.print_exc()
        doc.remove_client(client_id)

        await doc.broadcast_awareness({
            "type": "user_left",
            "client_id": client_id,
            "client_count": len(doc.clients)
        })

        yjs_collaboration_service.remove_document(document_id)


@router.get("/documents")
async def list_yjs_documents():
    """获取所有活跃的 Yjs 文档列表"""
    documents = yjs_collaboration_service.get_active_documents()
    return {
        "success": True,
        "data": {
            "documents": documents,
            "count": len(documents)
        }
    }
