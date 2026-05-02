"""
协作文档邀请管理API
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/collaboration/invites", tags=["collaboration-invites"])

# 简化的邀请存储(生产环境应使用数据库)
invitations_db = {}


class CreateInvitationRequest(BaseModel):
    """创建邀请请求"""
    document_id: str
    permission: str = "edit"  # edit or view
    expire_hours: int = 24  # 过期时间(小时)
    max_users: int = 3  # 最大用户数


class InvitationResponse(BaseModel):
    """邀请响应"""
    invite_id: str
    document_id: str
    invite_url: str
    permission: str
    expires_at: str
    max_users: int
    current_users: int


@router.post("/create", response_model=InvitationResponse)
async def create_invitation(request: CreateInvitationRequest):
    """
    创建协作文档邀请链接
    
    Args:
        request: 邀请配置
        
    Returns:
        邀请信息,包含邀请链接
    """
    try:
        print(f"Creating invitation for document: {request.document_id}")
        print(
            f"Request data: permission={request.permission}, expire_hours={request.expire_hours}, max_users={request.max_users}")

        # 验证输入参数
        if not request.document_id:
            raise HTTPException(status_code=400, detail="Document ID is required")

        if request.permission not in ["edit", "view"]:
            raise HTTPException(status_code=400, detail="Permission must be 'edit' or 'view'")

        if request.expire_hours <= 0:
            raise HTTPException(status_code=400, detail="Expire hours must be positive")

        if request.max_users <= 0:
            raise HTTPException(status_code=400, detail="Max users must be positive")

        # 生成唯一邀请ID
        invite_id = str(uuid.uuid4())

        # 计算过期时间
        expires_at = datetime.utcnow() + timedelta(hours=request.expire_hours)

        # 创建邀请记录
        invitation = {
            "invite_id": invite_id,
            "document_id": request.document_id,
            "permission": request.permission,
            "expires_at": expires_at,
            "max_users": request.max_users,
            "current_users": 0,
            "active_users": [],
            "created_at": datetime.utcnow(),
        }

        invitations_db[invite_id] = invitation

        # 生成邀请URL
        # 使用独立的协作房间页面
        base_url = "http://localhost:3000"  # 前端地址
        invite_url = f"{base_url}/collaboration/room?invite={invite_id}&doc={request.document_id}"

        print(f"Invitation created successfully: {invite_id}")

        return InvitationResponse(
            invite_id=invite_id,
            document_id=request.document_id,
            invite_url=invite_url,
            permission=request.permission,
            expires_at=expires_at.isoformat(),
            max_users=request.max_users,
            current_users=0,
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"Error creating invitation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create invitation: {str(e)}")


@router.get("/{invite_id}")
async def get_invitation(invite_id: str):
    """
    获取邀请详情
    
    Args:
        invite_id: 邀请ID
        
    Returns:
        邀请信息
    """
    invitation = invitations_db.get(invite_id)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # 检查是否过期
    if datetime.utcnow() > invitation["expires_at"]:
        raise HTTPException(status_code=410, detail="Invitation expired")

    return {
        "success": True,
        "data": {
            "invite_id": invite_id,
            "document_id": invitation["document_id"],
            "permission": invitation["permission"],
            "expires_at": invitation["expires_at"].isoformat(),
            "max_users": invitation["max_users"],
            "current_users": invitation["current_users"],
        }
    }


@router.post("/{invite_id}/accept")
async def accept_invitation(invite_id: str, user_info: dict = None):
    """
    接受邀请,加入协作文档
    
    Args:
        invite_id: 邀请ID
        user_info: 用户信息(可选)
        
    Returns:
        加入结果
    """
    invitation = invitations_db.get(invite_id)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # 检查是否过期
    if datetime.utcnow() > invitation["expires_at"]:
        raise HTTPException(status_code=410, detail="Invitation expired")

    # 检查人数限制
    if invitation["current_users"] >= invitation["max_users"]:
        raise HTTPException(
            status_code=403,
            detail=f"Maximum users ({invitation['max_users']}) reached"
        )

    # 更新邀请状态
    invitation["current_users"] += 1
    user_id = user_info.get("user_id",
                            f"guest_{uuid.uuid4().hex[:8]}") if user_info else f"guest_{uuid.uuid4().hex[:8]}"
    invitation["active_users"].append({
        "user_id": user_id,
        "joined_at": datetime.utcnow().isoformat()
    })

    return {
        "success": True,
        "data": {
            "document_id": invitation["document_id"],
            "permission": invitation["permission"],
            "user_id": user_id,
        }
    }


@router.get("/document/{document_id}/active")
async def get_active_invitations(document_id: str):
    """
    获取文档的活跃邀请列表
    
    Args:
        document_id: 文档ID
        
    Returns:
        活跃邀请列表
    """
    active_invites = []

    for invite_id, invitation in invitations_db.items():
        if (invitation["document_id"] == document_id and
                datetime.utcnow() <= invitation["expires_at"]):
            active_invites.append({
                "invite_id": invite_id,
                "permission": invitation["permission"],
                "expires_at": invitation["expires_at"].isoformat(),
                "max_users": invitation["max_users"],
                "current_users": invitation["current_users"],
                "invite_url": f"http://localhost:3000/collaboration/room?invite={invite_id}&doc={document_id}",
            })

    return {
        "success": True,
        "data": {
            "invitations": active_invites,
            "count": len(active_invites)
        }
    }


@router.delete("/{invite_id}")
async def revoke_invitation(invite_id: str):
    """
    撤销邀请
    
    Args:
        invite_id: 邀请ID
        
    Returns:
        操作结果
    """
    if invite_id not in invitations_db:
        raise HTTPException(status_code=404, detail="Invitation not found")

    del invitations_db[invite_id]

    return {
        "success": True,
        "message": "Invitation revoked"
    }
