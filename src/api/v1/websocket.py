"""
实时协作 WebSocket API
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from shared.services.collaboration import collaboration_service

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/collaborate/{document_id}")
async def collaborate_websocket(
        websocket: WebSocket,
        document_id: str,
        user_id: int = Query(..., description="用户ID")
):
    """
    实时协作编辑 WebSocket
    
    Args:
        websocket: WebSocket 连接
        document_id: 文档ID
        user_id: 用户ID
    """
    await collaboration_service.connect(document_id, user_id, websocket)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            # 处理操作
            op_type = data.get('type')

            if op_type == 'awareness':
                # 处理 awareness 更新
                await collaboration_service.update_awareness(
                    document_id=document_id,
                    user_id=user_id,
                    state=data.get('state', {})
                )
            else:
                # 处理编辑操作
                await collaboration_service.handle_operation(
                    document_id=document_id,
                    user_id=user_id,
                    operation=data
                )

    except WebSocketDisconnect:
        # 用户断开连接
        await collaboration_service.disconnect(document_id, user_id)

    except Exception as e:
        # 其他错误
        await collaboration_service.disconnect(document_id, user_id)
        raise
