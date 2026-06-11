"""
Edge Functions API
"""
from functools import wraps

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.services.integrations.edge_functions import edge_functions_service
from src.api.v2._helpers import ok, fail, _catch

router = APIRouter(tags=["edge-functions"])


class RegisterFunctionRequest(BaseModel):
    """注册函数请求"""
    name: str
    route: str
    cache_ttl: int = 0
    description: str = ""


@router.get("/list")
@_catch
async def list_functions():
    """列出所有 Edge Functions"""
    functions = edge_functions_service.list_functions()
    return ok(data=functions, msg=f"共 {len(functions)} 个函数")


@router.post("/register")
@_catch
async def register_function(request: RegisterFunctionRequest):
    """注册 Edge Function"""
    def default_handler(req):
        return {'message': f'Edge Function: {request.name}'}

    func = edge_functions_service.register_function(
        name=request.name, handler=default_handler,
        route=request.route, cache_ttl=request.cache_ttl,
        description=request.description
    )
    return ok(data=func.to_dict())


@router.delete("/items/{function_name}")
@_catch
async def remove_function(function_name: str):
    """移除 Edge Function"""
    success = edge_functions_service.remove_function(function_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Function '{function_name}' not found")
    return ok(data=None, msg=f"Function '{function_name}' removed")


@router.post("/generate/cloudflare")
@_catch
async def generate_cloudflare_worker():
    """生成 Cloudflare Workers 代码"""
    output_file = edge_functions_service.generate_cloudflare_worker()
    return ok(data={'output_file': output_file, 'message': 'Cloudflare Worker code generated successfully'})


@router.post("/generate/vercel")
@_catch
async def generate_vercel_edge_functions():
    """生成 Vercel Edge Functions 代码"""
    output_dir = edge_functions_service.generate_vercel_edge_function()
    return ok(data={'output_dir': output_dir, 'message': 'Vercel Edge Functions code generated successfully'})


def register_default_functions():
    """注册默认的 Edge Functions"""
    def article_cache_handler(request):
        return {'type': 'article_cache'}
    edge_functions_service.register_function(
        name='article-cache', handler=article_cache_handler,
        route='/api/articles/*', cache_ttl=300,
        description='Cache article API responses at edge'
    )

    def homepage_cache_handler(request):
        return {'type': 'homepage_cache'}
    edge_functions_service.register_function(
        name='homepage-cache', handler=homepage_cache_handler,
        route='/', cache_ttl=60,
        description='Cache homepage at edge'
    )

    def static_cache_handler(request):
        return {'type': 'static_cache'}
    edge_functions_service.register_function(
        name='static-cache', handler=static_cache_handler,
        route='/api/v2/static/*', cache_ttl=86400,
        description='Cache static assets at edge'
    )


register_default_functions()
