"""_pending_test_utility.py —— 待迁入 ``tests/`` 的 **纯函数** 单测

本任务环境**禁止写 ``tests/``、禁止执行 shell**，故把纯函数单测临时放在模块目录内
（文件名以下划线开头，不会被当作业务模块导入）。恢复后应移动到
``tests/api/v3/system/test_utility.py``。

只覆盖**不依赖 DB / 网络 / FastAPI** 的纯函数：

  - ``parse_command``        源 ``nlp_parser.parse_command`` 的薄封装（意图 / 实体 / 参数 / 报错）
  - ``intent_catalog``       源解析器的模式表读取
  - ``evaluate_user_vip``    源 ``user_defs.is_vip`` 判定（含过期 / 字符串 / 无 VIP）
  - ``expand_pattern``       源 ``block_pattern_defs.to_pattern_dict`` 展开

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/system/utility/_pending_test_utility.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故仅据逐行读过的实现静态编写。
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.utility.service import (
    evaluate_user_vip,
    expand_pattern,
    intent_catalog,
    parse_command,
)


# ------------------------------------------------------------------- 命令解析
def test_parse_command_create_article():
    result = parse_command("创建文章")
    assert result["intent"] == "create"
    assert result["entity_type"] == "article"
    assert 0.0 < result["confidence"] <= 1.0
    assert result["original_command"] == "创建文章"
    assert result["error"] is None


def test_parse_command_update_delete_query():
    assert parse_command("更新文章")["intent"] == "update"
    assert parse_command("删除用户")["intent"] == "delete"
    assert parse_command("删除用户")["entity_type"] == "user"
    assert parse_command("查看今天的文章")["intent"] == "query"


def test_parse_command_draft_and_status():
    result = parse_command("保存草稿")
    assert result["intent"] == "draft"
    assert result["parameters"]["status"] == "draft"


def test_parse_command_search_query_param():
    result = parse_command("搜索 关键词")
    assert result["intent"] == "search"
    assert result["parameters"]["query"] == "关键词"


def test_parse_command_extract_title_count_time_category_tags():
    assert parse_command("创建文章「标题TD」")["parameters"]["title"] == "标题TD"
    assert parse_command("删除3篇文章")["parameters"]["count"] == 3
    assert parse_command("查看今天的文章")["parameters"]["time_range"] == "today"
    assert parse_command("创建文章分类：技术")["parameters"]["category"] == "技术"
    assert parse_command("创建文章标签：a,b")["parameters"]["tags"] == ["a", "b"]


def test_parse_command_unrecognized_has_error():
    result = parse_command("xyzzy 无法识别的一句话")
    assert result["intent"] is None
    assert result["error"] == "无法识别意图"


def test_parse_command_blank_raises():
    with pytest.raises(BadRequestError):
        parse_command("   ")
    with pytest.raises(BadRequestError):
        parse_command("")


def test_parse_command_strips_whitespace():
    result = parse_command("  创建文章  ")
    assert result["intent"] == "create"
    assert result["original_command"] == "创建文章"


# ------------------------------------------------------------------- 能力目录
def test_intent_catalog_matches_source_enum():
    catalog = intent_catalog()
    assert "create" in catalog["intents"]
    assert "update" in catalog["intents"]
    assert "search" in catalog["intents"]
    assert catalog["intent_patterns"]["create"], "create 意图应有触发关键词"
    assert "article" in catalog["entity_types"]
    assert "user" in catalog["entity_types"]
    assert "today" in catalog["time_ranges"]


# ------------------------------------------------------------------- 用户 VIP
def test_evaluate_user_vip_level_only():
    # 无过期时间：只看 vip_level
    assert evaluate_user_vip(vip_level=0, vip_expires_at=None) is False
    assert evaluate_user_vip(vip_level=1, vip_expires_at=None) is True
    assert evaluate_user_vip(vip_level=None, vip_expires_at=None) is False


def test_evaluate_user_vip_datetime_expiry():
    future = datetime.now() + timedelta(days=1)
    past = datetime.now() - timedelta(days=1)
    assert evaluate_user_vip(vip_level=2, vip_expires_at=future) is True
    assert evaluate_user_vip(vip_level=2, vip_expires_at=past) is False


def test_evaluate_user_vip_string_expiry():
    future = (datetime.now() + timedelta(days=1)).isoformat()
    past = (datetime.now() - timedelta(days=1)).isoformat()
    assert evaluate_user_vip(vip_level=1, vip_expires_at=future) is True
    assert evaluate_user_vip(vip_level=1, vip_expires_at=past) is False


# --------------------------------------------------------------- 区块模式展开
def _pattern_row(**overrides):
    base = dict(
        name="hero",
        title="Hero 区块",
        description="desc",
        category="custom",
        blocks='[{"type": "hero", "text": "hi"}]',
        keywords="hero, banner",
        thumbnail=None,
        viewport_width=800,
        is_public=True,
        created_at=None,
        updated_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_expand_pattern_parses_blocks_and_keywords():
    out = expand_pattern(_pattern_row())
    assert out["name"] == "hero"
    assert out["category"] == "custom"
    assert out["blocks"] == [{"type": "hero", "text": "hi"}]
    assert out["keywords"] == ["hero", "banner"]
    assert out["is_public"] is True
    assert out["viewport_width"] == 800


def test_expand_pattern_empty_blocks_and_keywords():
    out = expand_pattern(_pattern_row(blocks=None, keywords=None))
    assert out["blocks"] == []
    assert out["keywords"] == []


def test_expand_pattern_keywords_trims_blank():
    out = expand_pattern(_pattern_row(keywords=" a , ,b "))
    assert out["keywords"] == ["a", "b"]
