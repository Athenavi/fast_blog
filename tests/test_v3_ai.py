"""ai 域（配置与执行引擎 / Agent 技能框架）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import asyncio
import json
import os
import pytest
import shared.config.settings  # noqa: E402,F401 - 触发 load_dotenv，让 DB_* 进入 os.environ
import shutil
import subprocess
import sys
import threading
import uuid
from fastapi import FastAPI
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from src.api.v3 import register_v3_routes
from src.api.v3.core import secret_box, user_secret_box
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.modules.ai import llm
from src.api.v3.modules.ai.skill import SKILL_CATEGORIES, registry
from src.api.v3.modules.ai.skill.builtin import CONTENT_ACTIONS, extract_keywords
from src.api.v3.modules.ai.skill.registry import SkillContext, SkillRegistry, SkillSpec
from src.api.v3.modules.ai.workflow import tasks

# ============================================================ 来自 test_v3_ai.py（16 项）
#: 项目根（跑 alembic 迁移用）
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_BASE = "/api/v3/ai/config"
WORKFLOW_BASE = "/api/v3/ai/workflow"

OPENAI_REPLY = "这是 OpenAI 兼容端点的回复"
ANTHROPIC_REPLY = "这是 Anthropic 端点的回复"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ================================================================ mock 模型端点
class _Recorder:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.status = 200
        self.payload: dict | None = None
        self.error_body: dict | None = None


def _handler_factory(recorder: _Recorder):
    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - http.server 约定
            length = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(length) if length else b''
            recorder.requests.append(
                {
                    'path': self.path,
                    'headers': {key: value for key, value in self.headers.items()},
                    'body': json.loads(raw.decode('utf-8') or '{}'),
                }
            )
            if recorder.error_body is not None:
                body = json.dumps(recorder.error_body).encode()
                status = recorder.status
            elif self.path.endswith('/v1/messages'):
                # Anthropic 形状
                body = json.dumps(
                    {
                        'id': 'msg_test',
                        'model': 'claude-test',
                        'content': [{'type': 'text', 'text': ANTHROPIC_REPLY}],
                        'usage': {'input_tokens': 11, 'output_tokens': 7},
                    }
                ).encode()
                status = 200
            else:
                # OpenAI 兼容形状
                body = json.dumps(
                    {
                        'id': 'chatcmpl-test',
                        'model': 'gpt-test',
                        'choices': [{'message': {'role': 'assistant', 'content': OPENAI_REPLY}}],
                        'usage': {'prompt_tokens': 13, 'completion_tokens': 5},
                    }
                ).encode()
                status = 200

            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:
            return

    return _Handler


@pytest.fixture()
def model_endpoint():
    """本地 mock 模型端点：返回 ``(base_url, recorder)``"""
    recorder = _Recorder()
    server = HTTPServer(('127.0.0.1', 0), _handler_factory(recorder))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", recorder
    finally:
        server.shutdown()
        server.server_close()


# ================================================================ 1. 路由与鉴权


# ================================================================ 2. 凭据加密（双因子）
def test_user_secret_key_depends_on_password_and_app_secret() -> None:
    cipher = user_secret_box.encrypt_for_user("sk-test", "hash-A")
    assert cipher != "sk-test"
    assert user_secret_box.decrypt_for_user(cipher, "hash-A") == "sk-test"
    # 换个用户（密码哈希不同）→ 解不开
    with pytest.raises(ValueError):
        user_secret_box.decrypt_for_user(cipher, "hash-B")


def test_user_secret_key_depends_on_app_secret(monkeypatch) -> None:
    """改 SECRET_KEY（app_secret_key）后，同一用户也解不开 —— 双因子都参与派生"""
    from shared.config.settings import settings

    cipher = user_secret_box.encrypt_for_user("sk-test", "hash-A")
    with monkeypatch.context() as patch:
        patch.setattr(settings, "SECRET_KEY", settings.SECRET_KEY + "-rotated")
        with pytest.raises(ValueError):
            user_secret_box.decrypt_for_user(cipher, "hash-A")


def test_user_secret_can_read_legacy_global_ciphertext() -> None:
    """老密文（全局 SECRET_KEY 加密）仍能读 —— 平滑迁移，不用重录"""
    legacy = secret_box.encrypt_secret("sk-legacy")
    assert user_secret_box.decrypt_for_user(legacy, "hash-A") == "sk-legacy"


def test_user_secret_derivation_is_stable() -> None:
    assert user_secret_box.derive_key("hash-A") == user_secret_box.derive_key("hash-A")
    assert user_secret_box.derive_key("hash-A") != user_secret_box.derive_key("hash-B")


# ================================================================ 3. 两套协议（真实 HTTP）
@pytest.mark.asyncio
async def test_openai_compatible_call(model_endpoint) -> None:
    endpoint, recorder = model_endpoint
    result = await llm.complete(
        llm.LLMSettings(
            provider="deepseek",  # 非 openai 字面量，但同协议
            api_url=f"{endpoint}/v1",
            api_key="sk-openai",
            model="gpt-test",
            max_tokens=64,
        ),
        system="你是助手",
        prompt="你好",
    )

    assert result.protocol == "openai"
    assert result.text == OPENAI_REPLY
    assert (result.prompt_tokens, result.completion_tokens) == (13, 5)

    sent = recorder.requests[0]
    assert sent['path'] == '/v1/chat/completions'
    headers = {key.lower(): value for key, value in sent['headers'].items()}
    assert headers['authorization'] == 'Bearer sk-openai'
    assert sent['body']['model'] == 'gpt-test'
    assert sent['body']['max_tokens'] == 64
    assert sent['body']['messages'] == [
        {'role': 'system', 'content': '你是助手'},
        {'role': 'user', 'content': '你好'},
    ]


@pytest.mark.asyncio
async def test_anthropic_call(model_endpoint) -> None:
    endpoint, recorder = model_endpoint
    result = await llm.complete(
        llm.LLMSettings(
            provider="anthropic",
            api_url=endpoint,
            api_key="sk-anthropic",
            model="claude-test",
            max_tokens=32,
        ),
        system="你是助手",
        prompt="你好",
    )

    assert result.protocol == "anthropic"
    assert result.text == ANTHROPIC_REPLY
    assert (result.prompt_tokens, result.completion_tokens) == (11, 7)

    sent = recorder.requests[0]
    assert sent['path'] == '/v1/messages'
    headers = {key.lower(): value for key, value in sent['headers'].items()}
    assert headers['x-api-key'] == 'sk-anthropic'
    assert headers['anthropic-version'] == llm.ANTHROPIC_DEFAULT_VERSION
    # Anthropic 的系统提示词在顶层 system，且 messages 里只有 user
    assert sent['body']['system'] == '你是助手'
    assert sent['body']['messages'] == [{'role': 'user', 'content': '你好'}]


@pytest.mark.asyncio
async def test_custom_endpoint_headers_and_api_version(model_endpoint) -> None:
    """自定义连接：extra_headers 可覆盖默认鉴权头，api_version 分别走 query / header"""
    endpoint, recorder = model_endpoint
    await llm.complete(
        llm.LLMSettings(
            provider="azure",  # OpenAI 兼容 + query 版本
            api_url=endpoint,
            api_key="ignored",
            model="m",
            api_version="2024-02-01",
            extra_headers={"api-key": "azure-key"},
        ),
        prompt="hi",
    )
    sent = recorder.requests[0]
    headers = {key.lower(): value for key, value in sent['headers'].items()}
    assert headers['api-key'] == 'azure-key'  # 自定义头覆盖默认
    assert 'api-version=2024-02-01' in sent['path']

    await llm.complete(
        llm.LLMSettings(
            provider="anthropic",
            api_url=endpoint,
            api_key="k",
            model="m",
            api_version="2024-01-01",
        ),
        prompt="hi",
    )
    headers2 = {key.lower(): value for key, value in recorder.requests[1]['headers'].items()}
    assert headers2['anthropic-version'] == '2024-01-01'


@pytest.mark.asyncio
async def test_llm_surfaces_vendor_error(model_endpoint) -> None:
    endpoint, recorder = model_endpoint
    recorder.status = 401
    recorder.error_body = {"error": {"message": "Incorrect API key provided"}}

    with pytest.raises(BadRequestError) as exc:
        await llm.complete(
            llm.LLMSettings(provider="openai", api_url=endpoint, api_key="bad", model="m"),
            prompt="hi",
        )
    assert "401" in str(exc.value)
    assert "Incorrect API key" in str(exc.value)


@pytest.mark.asyncio
async def test_llm_requires_model_and_prompt(model_endpoint) -> None:
    endpoint, _ = model_endpoint
    with pytest.raises(BadRequestError):
        await llm.complete(
            llm.LLMSettings(provider="openai", api_url=endpoint, api_key="k", model=""), prompt="hi"
        )
    with pytest.raises(BadRequestError):
        await llm.complete(
            llm.LLMSettings(provider="openai", api_url=endpoint, api_key="k", model="m"), prompt="  "
        )
    with pytest.raises(BadRequestError):
        await llm.complete(
            llm.LLMSettings(provider="openai", api_url="", api_key="k", model="m"), prompt="hi"
        )


def test_protocol_mapping() -> None:
    assert llm.protocol_for("openai") == "openai"
    assert llm.protocol_for("anthropic") == "anthropic"
    assert llm.protocol_for("claude") == "anthropic"
    assert llm.protocol_for("self-hosted-gateway") == "openai"  # 未知按兼容处理
    assert llm.protocol_for("") == "openai"


# ================================================================ 4. 任务模板
def test_task_templates_render() -> None:
    system, prompt = tasks.render("seo_optimize", input_text="正文内容")
    assert "SEO" in system
    assert "正文内容" in prompt

    _, translated = tasks.render("translate", input_text="hello", target_lang="日语")
    assert "日语" in translated

    _, custom = tasks.render("custom", input_text="随便问")
    assert custom == "随便问"

    with pytest.raises(KeyError):
        tasks.render("not-a-task", input_text="x")


def test_task_catalogue_covers_all_templates() -> None:
    names = {item["task_type"] for item in tasks.catalogue()}
    assert names == set(tasks.TASK_TEMPLATES)
    assert tasks.DEFAULT_TASK_TYPE in names


# ================================================================ 5. 执行引擎端到端（临时库）
PG_TOOLS = ("createdb", "dropdb")


def _pg_env() -> dict:
    env = os.environ.copy()
    password = os.getenv("DB_PASSWORD", "")
    if password:
        env["PGPASSWORD"] = password
    return env


def _db_args() -> list:
    return [
        "-h", os.getenv("DB_HOST", "localhost"),
        "-p", os.getenv("DB_PORT", "5432"),
        "-U", os.getenv("DB_USER", "postgres"),
    ]


@pytest.fixture()
def ai_database():
    """独立的临时库：**用 alembic 迁移**建全表 + 一个测试用户，用完 drop

    - 用独立库而不是项目库：测试会写 ``ai_configs`` / ``ai_workflows``，不污染真实数据；
    - 用 ``alembic upgrade head`` 而不是 ``create_all``：与生产建表路径一致
      （``create_all`` 会撞上模型里重复定义的索引），同时顺带验证迁移能在空库上跑通。
    """
    if not all(shutil.which(tool) for tool in PG_TOOLS):
        pytest.skip("缺少 createdb / dropdb")
    name = f"fb_ai_test_{uuid.uuid4().hex[:8]}"
    create = subprocess.run(
        ["createdb", *_db_args(), name], capture_output=True, text=True, env=_pg_env(), timeout=60
    )
    if create.returncode != 0:
        pytest.skip(f"无法创建临时库：{create.stderr.strip()[:150]}")

    url = (
        f"postgresql+asyncpg://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/{name}"
    )
    engine = None
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool

        migrate_env = _pg_env()
        # ⚠️ alembic/env.py 用 load_dotenv(override=True) 读 config/.env，
        # 因此 DB_NAME 会被 .env 里的值覆盖 —— 想把迁移指向临时库，只能设 DATABASE_URL
        # （.env 里没有这个键，所以不会被覆盖；env.py 的优先级也是 DATABASE_URL 最高）。
        migrate_env["DATABASE_URL"] = (
            f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}"
            f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{name}"
        )
        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            env=migrate_env,
            timeout=600,
        )
        if migrated.returncode != 0:
            pytest.skip(f"临时库迁移失败：{(migrated.stderr or migrated.stdout)[-300:]}")

        # NullPool：fixture 里用 asyncio.run 连接的循环会被关闭，池化连接跨循环复用会报
        # "Event loop is closed" —— 每次现连现断最省事
        engine = create_async_engine(url, poolclass=NullPool)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _create_user() -> int:
            async with session_factory() as db:
                # users 表只有 id 是 NOT NULL（其余列可空），只填必要字段
                result = await db.execute(
                    text(
                        "INSERT INTO users (username, email, password) "
                        "VALUES ('ai-test-user', 'ai-test@example.com', 'pbkdf2$test$hash') "
                        "RETURNING id"
                    )
                )
                await db.commit()
                return int(result.scalar())

        user_id = asyncio.run(_create_user())
        yield session_factory, user_id
    except Exception as exc:  # noqa: BLE001 - 准备失败就跳过，不阻塞其它测试
        pytest.skip(f"临时库准备失败：{exc}")
    finally:
        if engine is not None:
            asyncio.run(engine.dispose())
        subprocess.run(
            ["dropdb", "--if-exists", *_db_args(), name],
            capture_output=True,
            text=True,
            env=_pg_env(),
            timeout=60,
        )


@pytest.fixture()
def temp_backup_dir(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    return tmp_path


@pytest.mark.asyncio
async def test_execute_task_end_to_end(ai_database, model_endpoint, temp_backup_dir) -> None:
    """端到端：建配置（按用户密码加密）→ 真调 mock 模型 → 落库 completed + 结果 + tokens"""
    session_factory, user_id = ai_database
    endpoint, recorder = model_endpoint

    from src.api.v3.modules.ai.config.schema import AIConfigCreate
    from src.api.v3.modules.ai.config.service import ai_config_service
    from src.api.v3.modules.ai.workflow.schema import WorkflowExecute
    from src.api.v3.modules.ai.workflow.service import ai_workflow_service

    async with session_factory() as db:
        config = await ai_config_service.create_config(
            db,
            AIConfigCreate.model_validate(
                {
                    "user_id": user_id,
                    "name": "pytest-openai",
                    "api_url": f"{endpoint}/v1",
                    "api_key": "sk-pytest",
                    "model": "gpt-test",
                    "provider": "openai",
                    "max_tokens": 128,
                }
            ),
        )
        assert config["has_api_key"] is True
        assert "sk-pytest" not in str(config)  # 明文永不回传

        # 连接测试：真实调用一次
        tested = await ai_config_service.test_connection(db, config["id"])
        assert tested["ok"] is True
        assert tested["protocol"] == "openai"
        assert tested["reply"] == OPENAI_REPLY

        result = await ai_workflow_service.execute(
            db,
            WorkflowExecute.model_validate(
                {
                    "config_id": config["id"],
                    "task_type": "tag_recommend",
                    "input": "一篇讲 FastAPI 异步与 SQLAlchemy 的文章",
                }
            ),
        )
        assert result["status"] == "completed"
        assert result["tokens_used"] == 18  # 13 + 5
        assert result["model_used"] == "gpt-test"
        assert result["output_data"]["text"] == OPENAI_REPLY
        assert result["output_data"]["usage"] == {"prompt_tokens": 13, "completion_tokens": 5}

        # 重跑：沿用原输入
        retried = await ai_workflow_service.retry(db, result["id"])
        assert retried["status"] == "completed"
        assert retried["id"] != result["id"]

        # 库里的密文不是明文，且用该用户密码哈希能解回
        from shared.models.ai.ai_config import AIConfig

        row = await db.get(AIConfig, config["id"])
        assert row.api_key_encrypted and row.api_key_encrypted != "sk-pytest"
        assert user_secret_box.decrypt_for_user(row.api_key_encrypted, "pbkdf2$test$hash") == "sk-pytest"

    # 请求形状：第 1 次是"连接测试"，第 2 次才是 tag_recommend 任务
    assert len(recorder.requests) >= 3
    connection_body = recorder.requests[0]["body"]
    assert "连接测试" in connection_body["messages"][0]["content"]
    task_body = recorder.requests[1]["body"]
    assert task_body["messages"][0]["role"] == "system"
    assert "JSON 数组" in task_body["messages"][0]["content"]


@pytest.mark.asyncio
async def test_execute_records_failure(ai_database, model_endpoint, temp_backup_dir) -> None:
    """模型报错：落一条 failed 记录（带原因）并把错误抛给调用方"""
    session_factory, user_id = ai_database
    endpoint, recorder = model_endpoint
    recorder.status = 429
    recorder.error_body = {"error": {"message": "rate limit exceeded"}}

    from src.api.v3.modules.ai.config.schema import AIConfigCreate
    from src.api.v3.modules.ai.config.service import ai_config_service
    from src.api.v3.modules.ai.workflow.schema import WorkflowExecute
    from src.api.v3.modules.ai.workflow.service import ai_workflow_service

    async with session_factory() as db:
        config = await ai_config_service.create_config(
            db,
            AIConfigCreate.model_validate(
                {
                    "user_id": user_id,
                    "name": "pytest-failing",
                    "api_url": endpoint,
                    "api_key": "sk-x",
                    "model": "m",
                    "provider": "anthropic",
                }
            ),
        )
        with pytest.raises(BadRequestError) as exc:
            await ai_workflow_service.execute(
                db,
                WorkflowExecute.model_validate(
                    {"config_id": config["id"], "task_type": "summarize", "input": "内容"}
                ),
            )
        assert "rate limit" in str(exc.value)

        items, total = await ai_workflow_service.list_workflows(db, status="failed")
        assert total == 1
        assert items[0]["status"] == "failed"
        assert "rate limit" in items[0]["error_message"]
        assert items[0]["output_data"] is None


@pytest.mark.asyncio
async def test_execute_rejects_unknown_task_and_config(ai_database, temp_backup_dir) -> None:
    session_factory, user_id = ai_database
    from src.api.v3.modules.ai.workflow.schema import WorkflowExecute
    from src.api.v3.modules.ai.workflow.service import ai_workflow_service

    async with session_factory() as db:
        with pytest.raises(BadRequestError) as exc:
            await ai_workflow_service.execute(
                db,
                WorkflowExecute.model_validate(
                    {"config_id": 1, "task_type": "nope", "input": "x"}
                ),
            )
        assert "未知任务类型" in str(exc.value)


@pytest.mark.asyncio
async def test_config_rejects_unreadable_credentials(ai_database, temp_backup_dir) -> None:
    """密钥与当前用户密码不匹配（等价于"用户改过密码"）→ 明确报"重新填写"，不是静默当空值"""
    session_factory, user_id = ai_database
    from shared.models.ai.ai_config import AIConfig

    from src.api.v3.modules.ai.config.schema import AIConfigCreate
    from src.api.v3.modules.ai.config.service import ai_config_service

    async with session_factory() as db:
        config = await ai_config_service.create_config(
            db,
            AIConfigCreate.model_validate(
                {
                    "user_id": user_id,
                    "name": "pytest-rotate",
                    "api_url": "http://127.0.0.1:1",
                    "api_key": "sk-rotate",
                    "model": "m",
                }
            ),
        )
        # 模拟"密码已变更"：把密文换成用另一把用户密钥加密的（不改 users 表）
        row = await db.get(AIConfig, config["id"])
        row.api_key_encrypted = user_secret_box.encrypt_for_user("sk-rotate", "another-password-hash")
        await db.commit()

        with pytest.raises(BadRequestError) as exc:
            await ai_config_service.resolve_llm_settings(db, config["id"])
        assert "重新填写" in str(exc.value)


# ============================================================ 来自 test_v3_ai_skill.py（16 项）
BASE = "/api/v3/ai/skill"


def _app__ai_skill() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 关键词提取
def test_extract_keywords_returns_scored_ngrams():
    text = "数据分析是数据分析的核心。数据分析帮助我们理解数据，数据分析驱动决策。"

    keywords = extract_keywords(text, limit=5)

    assert keywords
    top = keywords[0]
    assert "数据" in top["keyword"]
    assert top["count"] >= 2
    assert top["score"] > 0


def test_extract_keywords_filters_cross_boundary_noise_by_default():
    """默认 min_count=2：只出现一次的跨词拼接片段不应出现在结果里"""
    text = "内容营销策略很重要。内容营销策略需要长期投入与数据分析。"

    keywords = extract_keywords(text, limit=10)

    assert keywords
    assert all(item["count"] >= 2 for item in keywords)
    assert "内容营销策略" in [item["keyword"] for item in keywords]
    # min_count=1 时才允许单次候选（长尾词场景）
    loose = extract_keywords(text, limit=20, min_count=1)
    assert any(item["count"] == 1 for item in loose)


def test_extract_keywords_raises_when_nothing_meets_threshold():
    with pytest.raises(BadRequestError):
        extract_keywords("独一无二的短语只出现一次", min_count=5)


def test_extract_keywords_strips_html():
    keywords = extract_keywords("<p>Python <strong>异步编程</strong> 与 异步编程</p>", limit=5)

    joined = " ".join(item["keyword"] for item in keywords)
    assert "异步编程" in joined
    assert "<" not in joined


def test_extract_keywords_keeps_longer_phrase_over_substring():
    text = "内容营销策略很重要。内容营销策略需要长期投入。内容营销策略离不开内容营销策略的执行。"

    keywords = extract_keywords(text, limit=3)

    assert "内容营销策略" in [item["keyword"] for item in keywords]


def test_extract_keywords_picks_latin_words():
    keywords = extract_keywords("FastAPI and FastAPI routers, FastAPI async.", limit=5)

    assert "fastapi" in [item["keyword"] for item in keywords]


@pytest.mark.parametrize("bad", ["", "   ", "<p></p>"])
def test_extract_keywords_rejects_empty(bad):
    with pytest.raises(BadRequestError):
        extract_keywords(bad)


def test_content_actions_map_to_known_task_types():
    from src.api.v3.modules.ai.workflow import tasks

    assert set(CONTENT_ACTIONS.values()) <= set(tasks.TASK_TEMPLATES)


# ------------------------------------------------------------------ 注册表
def _spec(name: str, category: str = "data_analysis") -> SkillSpec:
    async def handler(_ctx):  # pragma: no cover - 只用于注册
        return {}

    return SkillSpec(
        name=name,
        label=name,
        description="测试技能",
        category=category,
        required_permission=None,
        params=(),
        handler=handler,
    )


def test_registry_rejects_duplicate_name():
    local = SkillRegistry()
    local.register(_spec("dup"))

    with pytest.raises(ValueError):
        local.register(_spec("dup"))


def test_registry_rejects_unknown_category():
    with pytest.raises(ValueError):
        SkillRegistry().register(_spec("bad", category="not_a_category"))


def test_registry_get_missing_raises_not_found():
    with pytest.raises(NotFoundError):
        SkillRegistry().get("nope")


def test_registry_filters_by_category_and_keyword():
    local = SkillRegistry()
    local.register(_spec("alpha", category="data_analysis"))
    local.register(_spec("beta", category="system_ops"))

    assert [item["name"] for item in local.list_skills(category="system_ops")] == ["beta"]
    assert [item["name"] for item in local.list_skills(keyword="alph")] == ["alpha"]
    assert len(local.list_skills()) == 2


def test_skill_context_helpers():
    ctx = SkillContext(db=None, params={"n": "3", "empty": ""})

    assert ctx.param("missing", "d") == "d"
    assert ctx.param("empty", "d") == "d"
    assert ctx.int_param("n") == 3
    # 空值走默认；非数字要报 400 而不是静默按 None 处理
    assert ctx.int_param("empty", default=7) == 7
    with pytest.raises(BadRequestError):
        ctx.require("missing")
    with pytest.raises(BadRequestError):
        SkillContext(db=None, params={"n": "abc"}).int_param("n")


# ------------------------------------------------------------------ 内置技能
def test_builtin_skills_registered():
    names = set(registry.names())

    assert {
               "content_creator",
               "seo_optimizer",
               "keyword_extract",
               "content_stats",
               "migration_preview",
               "ops_health",
           } <= names


def test_every_builtin_skill_has_valid_category_and_meta():
    for name in registry.names():
        spec = registry.get(name)
        assert spec.category in SKILL_CATEGORIES
        assert spec.label and spec.description
        assert callable(spec.handler)


def test_skills_declaring_permission_use_real_codes():
    from src.api.v3.core.permission.codes import all_codes

    known = set(all_codes())

    for name in registry.names():
        spec = registry.get(name)
        if spec.required_permission:
            assert spec.required_permission in known, name

# ------------------------------------------------------------------ 端点
