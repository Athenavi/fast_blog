"""
NFT 管理 API
提供 NFT 铸造、查询、验证等功能
"""
from functools import wraps
from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.services.integrations.nft_service import nft_service
from src.api.v2._helpers import ok, fail, _catch

router = APIRouter(tags=["NFT"])


class MintNFTRequest(BaseModel):
    """铸造 NFT 请求"""
    article_id: int
    owner_address: str


class TransferNFTRequest(BaseModel):
    """转移 NFT 请求"""
    article_id: int
    new_owner_address: str


class VerifyOwnershipRequest(BaseModel):
    """验证所有权请求"""
    article_id: int
    wallet_address: str


@router.post("/mint")
@_catch
async def mint_nft(request: MintNFTRequest):
    """为文章铸造 NFT"""
    article_data = {
        "id": request.article_id, "title": f"Article {request.article_id}",
        "excerpt": "This is a sample article", "cover_image": "",
        "author": request.owner_address, "content": "Sample content",
        "type": "blog", "tags": ["sample"], "created_at": "2024-01-01T00:00:00"
    }
    nft_record = nft_service.mint_nft(article_data, request.owner_address)
    if not nft_record:
        raise HTTPException(status_code=500, detail="NFT 铸造失败")
    return ok(data={
        "token_id": nft_record.token_id, "contract_address": nft_record.contract_address,
        "owner_address": nft_record.owner_address, "metadata_uri": nft_record.metadata_uri,
        "article_id": nft_record.article_id, "minted_at": nft_record.minted_at,
        "transaction_hash": nft_record.transaction_hash, "network": nft_record.network
    }, message="NFT 铸造成功")


@router.get("/{article_id}")
@_catch
async def get_nft_info(article_id: int):
    """获取文章的 NFT 信息"""
    nft_info = nft_service.get_nft_info(article_id)
    if not nft_info:
        raise HTTPException(status_code=404, detail="该文章尚未铸造 NFT")
    return ok(data=nft_info)


@router.post("/verify")
@_catch
async def verify_ownership(request: VerifyOwnershipRequest):
    """验证钱包地址是否拥有文章的 NFT"""
    is_owner = nft_service.verify_ownership(request.article_id, request.wallet_address)
    return ok(data={"article_id": request.article_id, "wallet_address": request.wallet_address, "is_owner": is_owner})


@router.get("/user/{wallet_address}")
@_catch
async def get_user_nfts(wallet_address: str):
    """获取用户拥有的所有 NFT"""
    nfts = nft_service.get_user_nfts(wallet_address)
    return ok(data={"wallet_address": wallet_address, "total_nfts": len(nfts), "nfts": nfts})


@router.post("/transfer")
@_catch
async def transfer_nft(request: TransferNFTRequest):
    """转移 NFT 所有权"""
    success = nft_service.transfer_nft(request.article_id, request.new_owner_address)
    if not success:
        raise HTTPException(status_code=400, detail="NFT 转移失败")
    return ok(data={"article_id": request.article_id, "new_owner": request.new_owner_address},
              message="NFT 所有权已转移")


@router.get("/metadata/{article_id}")
@_catch
async def get_nft_metadata(article_id: int):
    """获取 NFT 元数据"""
    article_data = {
        "id": article_id, "title": f"Article {article_id}",
        "excerpt": "This is a sample article", "cover_image": "",
        "author": "0x0000000000000000000000000000000000000000",
        "content": "Sample content", "type": "blog", "tags": ["sample"],
        "created_at": "2024-01-01T00:00:00"
    }
    metadata = nft_service.generate_metadata(article_data)
    return ok(data=metadata.to_dict())


@router.post("/configure")
@_catch
async def configure_nft_service(config: Dict[str, str]):
    """配置 NFT 服务"""
    nft_service.configure(config)
    return ok(data=None, message="NFT 服务配置已更新")
