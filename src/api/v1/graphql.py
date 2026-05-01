"""
GraphQL API 路由

提供 GraphQL endpoint 和 GraphiQL 界面
"""
from fastapi import APIRouter, Request
from strawberry.fastapi import GraphQLRouter

from src.api.v1.graphql_schema import schema

router = APIRouter(prefix="/graphql", tags=["graphql"])

# 创建 GraphQL router
graphql_app = GraphQLRouter(
    schema,
    graphiql=True,  # 启用 GraphiQL 界面
)

# 挂载 GraphQL app
router.mount("/", app=graphql_app)


@router.get("/")
async def graphql_playground():
    """
    GraphQL Playground 重定向
    
    访问 /graphql 会自动跳转到 GraphiQL 界面
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/graphql")
