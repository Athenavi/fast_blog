"""测试：后台菜单模块（admin_menu）与种子脚本的 menus.ts 解析器

不需要数据库：

  - 路由挂载与鉴权用 ``TestClient`` 走 401 路径
  - 解析器与 ``menu_type`` 是纯函数，直接断言（**解析器写错过一次**：子节点的父取了错位索引）

真正需要 DB 的行为（角色授权、祖先补齐、登录下发）留待集成 / 冒烟验证。
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.seed_admin_menus import parse_menus_ts, to_menu_rows
from src.api.v3 import register_v3_routes
from src.api.v3.modules.system.admin_menu.schema import (
    MENU_TYPE_BUTTON,
    MENU_TYPE_DIR,
    MENU_TYPE_MENU,
)

MINI_MENUS_TS = """
export const ADMIN_MENUS: AdminMenuItem[] = [
  {
    name: 'Dashboard',
    path: '/dashboard',
    title: '仪表盘',
    permission: 'settings:view',
    order: 1,
  },
  {
    name: 'Content',
    path: '/content',
    title: '内容管理',
    order: 2,
    children: [
      {name: 'ArticleList', path: '/content/article', title: '文章', permission: 'article:view'},
      {
        name: 'DeepDir',
        path: '/content/deep',
        title: '深层',
        children: [
          {
            name: 'DeepLeaf',
            path: '/content/deep/leaf',
            title: '叶子',
          },
        ],
      },
    ],
  },
  {
    name: 'Login',
    path: '/login',
    title: '登录',
    hidden: true,
  },
]
"""


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 路由


def test_admin_menu_requires_auth():
    client = TestClient(_app(), raise_server_exceptions=False)
    for path in (
            "/api/v3/system/admin-menu",
            "/api/v3/system/admin-menu/tree",
            "/api/v3/system/admin-menu/my",
            "/api/v3/system/admin-menu/1",
            "/api/v3/system/admin-menu/role/1",
    ):
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} 应要求登录"


# ------------------------------------------------------------------ 纯函数
def test_menu_type_constants_align_with_official():
    """对齐官方 sys_menu：1 目录 / 2 菜单 / 3 按钮"""
    assert (MENU_TYPE_DIR, MENU_TYPE_MENU, MENU_TYPE_BUTTON) == (1, 2, 3)


def test_parser_extracts_hierarchy_and_skips_hidden():
    entries = parse_menus_ts(MINI_MENUS_TS)
    codes = [entry["code"] for entry in entries]
    # 解析阶段会看到全部路由（含 hidden）；hidden 只在生成菜单行时被跳过
    assert codes == ["Dashboard", "Content", "ArticleList", "DeepDir", "DeepLeaf", "Login"]

    parents = {entry["code"]: entry.get("parent_code") for entry in entries}
    assert parents["Dashboard"] is None
    assert parents["Content"] is None
    assert parents["ArticleList"] == "Content"
    assert parents["DeepDir"] == "Content"
    # 多层嵌套：叶子挂到 DeepDir，而不是 Content
    assert parents["DeepLeaf"] == "DeepDir"

    rows = {row["code"]: row for row in to_menu_rows(entries)}
    assert "Login" not in rows, "hidden 路由不应入库"
    assert rows["Content"]["menu_type"] == MENU_TYPE_DIR
    assert rows["ArticleList"]["menu_type"] == MENU_TYPE_MENU
    assert rows["ArticleList"]["permission_code"] == "article:view"
    assert rows["DeepDir"]["title"] == "深层"
    # 父节点必须先于子节点入库（种子脚本按此顺序解析 parent_id）
    ordered = [row["code"] for row in to_menu_rows(entries)]
    assert ordered.index("Content") < ordered.index("ArticleList")
