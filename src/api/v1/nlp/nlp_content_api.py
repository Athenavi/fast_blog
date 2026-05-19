"""
自然语言内容管理 API

提供基于自然语言的内容管理接口
"""

from fastapi import APIRouter, Depends, Body

from shared.services.nlp.nlp_command_parser import nlp_parser, batch_manager
from src.api.v1.core.responses import ApiResponse
from src.api.v1.users.user_management import jwt_required

router = APIRouter(prefix="/nlp", tags=["NLP Content Management"])


@router.post("/parse")
async def parse_command(
        command: str = Body(..., description="自然语言命令"),
        current_user=Depends(jwt_required)
):
    """
    解析自然语言命令
    
    将用户的自然语言指令转换为结构化的操作参数
    """
    result = nlp_parser.parse_command(command)

    if "error" in result:
        return ApiResponse(
            success=False,
            error=result["error"]
        )

    return ApiResponse(
        success=True,
        data=result
    )


@router.post("/execute")
async def execute_nlp_command(
        command: str = Body(..., description="自然语言命令"),
        current_user=Depends(jwt_required)
):
    """
    执行自然语言命令
    
    解析并执行用户的自然语言指令
    """
    # 解析命令
    parsed = nlp_parser.parse_command(command)

    if "error" in parsed:
        return ApiResponse(
            success=False,
            error=parsed["error"]
        )

    intent = parsed.get("intent")
    parameters = parsed.get("parameters", {})

    # 根据意图执行相应操作
    try:
        if intent == "create":
            result = await _handle_create(parameters)
        elif intent == "update":
            result = await _handle_update(parameters)
        elif intent == "delete":
            result = await _handle_delete(parameters)
        elif intent == "query":
            result = await _handle_query(parameters)
        elif intent == "publish":
            result = await _handle_publish(parameters)
        elif intent == "search":
            result = await _handle_search(parameters)
        else:
            return ApiResponse(
                success=False,
                error=f"Unsupported intent: {intent}"
            )

        return ApiResponse(
            success=True,
            data={
                "parsed_command": parsed,
                "execution_result": result
            }
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e)
        )


@router.post("/batch/execute")
async def execute_batch_operation(
        operation_type: str = Body(..., description="操作类型 (publish/draft/delete/update)"),
        items: list = Body(..., description="要操作的项目列表"),
        parameters: dict = Body({}, description="操作参数"),
        current_user=Depends(jwt_required)
):
    """
    执行批量操作
    
    支持批量发布、批量删除等操作
    """
    result = await batch_manager.execute_batch_operation(
        operation_type=operation_type,
        items=items,
        parameters=parameters
    )

    return ApiResponse(
        success=result["success"],
        data=result
    )


@router.get("/batch/history")
async def get_batch_history(
        limit: int = 10,
        current_user=Depends(jwt_required)
):
    """
    获取批量操作历史
    
    查看最近执行的批量操作记录
    """
    history = batch_manager.get_operation_history(limit=limit)

    return ApiResponse(
        success=True,
        data={
            "history": history,
            "total": len(history)
        }
    )


@router.post("/batch/rollback/{operation_id}")
async def rollback_batch_operation(
        operation_id: str,
        current_user=Depends(jwt_required)
):
    """
    回滚批量操作
    
    撤销之前执行的批量操作
    """
    result = await batch_manager.rollback_operation(operation_id)

    return ApiResponse(
        success=result["success"],
        data=result,
        message=result.get("message")
    )


@router.get("/examples")
async def get_command_examples(current_user=Depends(jwt_required)):
    """
    获取命令示例
    
    提供常用的自然语言命令示例
    """
    examples = {
        "content_creation": [
            {
                "command": "创建一篇关于Python编程的文章",
                "description": "创建新文章",
                "intent": "create",
                "entity": "article"
            },
            {
                "command": "新建帖子「机器学习入门」，分类为技术",
                "description": "创建带分类的文章",
                "intent": "create",
                "entity": "article"
            },
            {
                "command": "保存草稿「我的想法」",
                "description": "保存为草稿",
                "intent": "draft",
                "entity": "article"
            }
        ],
        "content_management": [
            {
                "command": "更新文章标题为「新标题」",
                "description": "更新文章",
                "intent": "update",
                "entity": "article"
            },
            {
                "command": "删除这篇文章",
                "description": "删除文章",
                "intent": "delete",
                "entity": "article"
            },
            {
                "command": "发布所有本周的草稿",
                "description": "批量发布",
                "intent": "batch",
                "entity": "article"
            }
        ],
        "content_query": [
            {
                "command": "查询所有已发布的文章",
                "description": "查询文章",
                "intent": "query",
                "entity": "article"
            },
            {
                "command": "列出本周的所有帖子",
                "description": "列出文章",
                "intent": "query",
                "entity": "article"
            },
            {
                "command": "搜索关于AI的文章",
                "description": "搜索文章",
                "intent": "search",
                "entity": "article"
            }
        ],
        "batch_operations": [
            {
                "command": "批量删除所有草稿",
                "description": "批量删除",
                "intent": "batch",
                "operation": "delete"
            },
            {
                "command": "全部发布本月的文章",
                "description": "批量发布",
                "intent": "batch",
                "operation": "publish"
            },
            {
                "command": "将所有文章标记为草稿",
                "description": "批量更新状态",
                "intent": "batch",
                "operation": "update"
            }
        ]
    }

    return ApiResponse(
        success=True,
        data=examples
    )


@router.get("/guide")
async def get_nlp_guide(current_user=Depends(jwt_required)):
    """
    获取 NLP 内容管理使用指南
    """
    guide = {
        "overview": {
            "title": "自然语言内容管理系统",
            "description": "通过自然语言指令管理博客内容，支持创建、更新、删除、查询等操作。",
            "version": "1.0.0"
        },
        "features": [
            "智能意图识别 - 自动识别用户操作意图",
            "参数提取 - 从自然语言中提取关键参数",
            "批量操作 - 支持批量处理多个项目",
            "操作历史 - 记录所有操作，支持回滚",
            "多语言支持 - 支持中英文混合输入"
        ],
        "supported_intents": [
            {
                "name": "create",
                "description": "创建新内容",
                "keywords": ["创建", "新建", "添加", "create", "new", "add"]
            },
            {
                "name": "update",
                "description": "更新现有内容",
                "keywords": ["更新", "修改", "编辑", "update", "edit", "modify"]
            },
            {
                "name": "delete",
                "description": "删除内容",
                "keywords": ["删除", "移除", "delete", "remove"]
            },
            {
                "name": "query",
                "description": "查询内容",
                "keywords": ["查询", "查看", "显示", "query", "view", "show"]
            },
            {
                "name": "publish",
                "description": "发布内容",
                "keywords": ["发布", "上线", "publish"]
            },
            {
                "name": "search",
                "description": "搜索内容",
                "keywords": ["搜索", "查找", "search", "find"]
            },
            {
                "name": "batch",
                "description": "批量操作",
                "keywords": ["批量", "全部", "所有", "batch", "all"]
            }
        ],
        "usage_tips": [
            "使用引号标注标题：创建文章「我的标题」",
            "指定分类：分类为技术",
            "添加标签：标签：Python,AI",
            "时间范围：本周、本月、今天",
            "数量限制：5篇文章"
        ],
        "api_endpoints": {
            "parse_command": "POST /nlp/parse - 解析命令",
            "execute_command": "POST /nlp/execute - 执行命令",
            "batch_execute": "POST /nlp/batch/execute - 批量执行",
            "batch_history": "GET /nlp/batch/history - 查看历史",
            "batch_rollback": "POST /nlp/batch/rollback/{id} - 回滚操作"
        }
    }

    return ApiResponse(
        success=True,
        data=guide
    )


# ==================== 内部处理函数 ====================

async def _handle_create(parameters: dict) -> dict:
    """处理创建操作"""
    # TODO: 实际实现需要调用文章服务
    return {
        "action": "create",
        "status": "completed",
        "message": "Content created successfully"
    }


async def _handle_update(parameters: dict) -> dict:
    """处理更新操作"""
    # TODO: 实际实现需要调用文章服务
    return {
        "action": "update",
        "status": "completed",
        "message": "Content updated successfully"
    }


async def _handle_delete(parameters: dict) -> dict:
    """处理删除操作"""
    # TODO: 实际实现需要调用文章服务
    return {
        "action": "delete",
        "status": "completed",
        "message": "Content deleted successfully"
    }


async def _handle_query(parameters: dict) -> dict:
    """处理查询操作"""
    # TODO: 实际实现需要调用文章服务
    return {
        "action": "query",
        "status": "completed",
        "data": []
    }


async def _handle_publish(parameters: dict) -> dict:
    """处理发布操作"""
    # TODO: 实际实现需要调用文章服务
    return {
        "action": "publish",
        "status": "completed",
        "message": "Content published successfully"
    }


async def _handle_search(parameters: dict) -> dict:
    """处理搜索操作"""
    query = parameters.get("query", "")

    # TODO: 实际实现需要调用搜索服务
    return {
        "action": "search",
        "query": query,
        "status": "completed",
        "results": []
    }
