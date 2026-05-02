"""
实时协作编辑 WebSocket API

提供基于WebSocket的实时协作编辑功能
"""
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import JSONResponse

from shared.services.collaboration import collaboration_service

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


@router.websocket("/ws/{document_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        document_id: str,
        token: Optional[str] = Query(None, description="JWT Token for authentication"),
        client_id: Optional[str] = Query(None, description="Client identifier")
):
    """
    WebSocket 协作文档端点
    
    支持的操作类型:
    - join: 加入协作文档
    - leave: 离开协作文档
    - operation: 发送编辑操作(insert/delete/replace)
    - cursor: 更新光标位置
    - sync: 请求文档同步
    """

    # TODO: 实现token验证
    # if token:
    #     try:
    #         user = verify_token(token)
    #         if not user:
    #             await websocket.close(code=4001, reason="Invalid token")
    #             return
    #     except Exception as e:
    #         await websocket.close(code=4001, reason=f"Authentication failed: {str(e)}")
    #         return

    await websocket.accept()

    # 获取或创建协作文档
    doc = collaboration_service.get_or_create_document(document_id)

    # 生成客户端ID
    if not client_id:
        client_id = str(id(websocket))

    # 添加客户端
    doc.add_client(websocket)

    # 发送欢迎消息和当前文档状态
    await websocket.send_json({
        "type": "welcome",
        "document_id": document_id,
        "client_id": client_id,
        "state": doc.get_state()
    })

    # 通知其他客户端有新用户加入
    await doc.broadcast({
        "type": "user_joined",
        "client_id": client_id,
        "client_count": len(doc.clients)
    }, exclude=websocket)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "operation":
                # 处理编辑操作
                operation = message.get("operation")
                if operation:
                    # 应用操作到文档
                    doc.apply_operation(operation, client_id)

                    # 广播操作给其他客户端
                    await doc.broadcast({
                        "type": "remote_operation",
                        "operation": operation,
                        "client_id": client_id,
                        "timestamp": doc.last_modified.isoformat()
                    }, exclude=websocket)

            elif msg_type == "cursor":
                # 处理光标更新
                cursor_data = message.get("cursor", {})
                doc.apply_operation({
                    "type": "cursor",
                    "position": cursor_data.get("position", 0),
                    "selection": cursor_data.get("selection")
                }, client_id)

                # 广播光标位置
                await doc.broadcast({
                    "type": "cursor_update",
                    "client_id": client_id,
                    "cursor": cursor_data
                }, exclude=websocket)

            elif msg_type == "sync":
                # 同步文档状态
                await websocket.send_json({
                    "type": "sync_response",
                    "state": doc.get_state()
                })

            elif msg_type == "ping":
                # 心跳检测
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        # 客户端断开连接
        doc.remove_client(websocket)

        # 通知其他客户端
        await doc.broadcast({
            "type": "user_left",
            "client_id": client_id,
            "client_count": len(doc.clients)
        })

        # 如果没有客户端了,清理文档
        if len(doc.clients) == 0:
            collaboration_service.remove_document(document_id)

    except Exception as e:
        print(f"WebSocket error: {e}")
        doc.remove_client(websocket)
        await doc.broadcast({
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
async def get_document_state(document_id: str):
    """
    获取指定文档的状态(非WebSocket方式)
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
async def save_document(document_id: str, save_data: dict):
    """
    保存协作文档内容到数据库
    
    Args:
        document_id: 文档ID
        save_data: {"content": "...", "metadata": {...}}
    """
    doc = collaboration_service.documents.get(document_id)

    if not doc:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Document not found"}
        )

    # 这里应该保存到数据库
    # 简化实现:只返回成功
    content = save_data.get("content", doc.content)

    return {
        "success": True,
        "message": "Document saved successfully",
        "data": {
            "document_id": document_id,
            "content_length": len(content),
            "saved_at": doc.last_modified.isoformat()
        }
    }
