"""通用工作流引擎（v3）：把 v2 的 ``shared/services/system/workflow_engine.py`` 接线到 v3

v2 的引擎把**全部状态放在进程内存**里（定义字典 / 实例字典 / 全局执行历史列表），
进程一重启全丢；而且它的 ``approval`` 节点**自动通过**、未知 ``action`` **静默成功**
（``else: return {'action': action_type, 'executed': True}``），条件也只支持 equality。

v3 保留 v2 的语义（定义注册 / 实例执行 / 逐节点推进 / 条件分支 / 执行历史），但：

  1. **状态全部落库**：统一写 ``system_settings``（不新建表）。定义存键
     ``workflow.definitions``（JSON 对象 ``{workflow_id: definition}``），实例与执行记录
     存键 ``workflow.instances``（JSON 数组，最多保留最近 ``MAX_INSTANCES`` 条，超出按
     时间淘汰）。落点列名 ``setting_key`` / ``setting_value`` 取自
     ``shared/models/system/system_settings.py``（``setting_value`` 是 ``Text``）。
  2. **未知动作如实失败**：``action`` 节点只认一组内建动作，不认识就抛错，节点 failed +
     实例 failed，不再静默成功。
  3. **审批不自动通过**：``approval`` 节点把实例停在 ``pending_approval`` 并写入
     ``awaiting_node``，由 ``approve`` / ``reject`` 推进。
  4. **每一步都落库**：``history`` 记录 ``node_started`` / ``node_finished`` /
     ``awaiting_approval`` / ``approved`` / ``rejected`` / ``failed`` / ``completed`` /
     ``cancelled`` 等事件。

与 DB 无关的纯逻辑（``validate_definition`` / ``evaluate_condition`` / ``can_transition``）
与读写分离，便于在无数据库场景下测试。
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.workflow")

# ------------------------------------------------------------------ 存储键
#: 工作流定义集合在 ``system_settings`` 里的键（JSON 对象 ``{workflow_id: definition}``）
DEFINITIONS_KEY = "workflow.definitions"
#: 工作流实例与执行记录在 ``system_settings`` 里的键（JSON 数组）
INSTANCES_KEY = "workflow.instances"
#: 实例数组最多保留的条数（超出按 created_at 时间倒序淘汰）
MAX_INSTANCES = 200

# ------------------------------------------------------------------ 枚举
#: 节点类型
NODE_TYPES = ("action", "condition", "approval")
#: 实例基本状态
INSTANCE_STATUS = ("pending", "running", "completed", "failed", "cancelled")
#: 审批暂停态（不在 ``INSTANCE_STATUS`` 里，是一个额外的运行期态）
STATUS_PENDING_APPROVAL = "pending_approval"
#: 终态集合（不可再流转）
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

#: 状态机：合法转移表（``can_transition`` 依据它判定）
ALLOWED_TRANSITIONS: Dict[str, frozenset] = {
    "pending": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"pending_approval", "completed", "failed", "cancelled"}),
    "pending_approval": frozenset({"running", "completed", "failed", "cancelled"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}

#: 内建 action（``action`` 节点 ``config.action`` 只认这些）
BUILTIN_ACTIONS = ("log", "set_context", "http_request", "sleep")
#: 受限条件比较支持的运算符
CONDITION_OPS = (">", ">=", "<", "<=", "==", "!=")
#: ``sleep`` 动作允许的秒数区间（避免节点把执行线程挂住太久）
SLEEP_MIN_SECONDS = 1
SLEEP_MAX_SECONDS = 5
#: ``http_request`` 默认超时（秒）
HTTP_TIMEOUT_SECONDS = 10.0
#: ``http_request`` 响应体保留的最大字符数
HTTP_RESPONSE_MAX_CHARS = 2000
#: workflow_id 长度上限
MAX_WORKFLOW_ID_LEN = 100


# ================================================================== 纯函数
def _now_iso() -> str:
    """当前时间的 ISO 字符串（本地时区，秒级可读）"""
    return datetime.now().isoformat()


def validate_workflow_id(workflow_id: Any) -> str:
    """校验并归一化 ``workflow_id``，非法时抛 ``BadRequestError``"""
    if not isinstance(workflow_id, str):
        raise BadRequestError("workflow_id 必须是字符串")
    workflow_id = workflow_id.strip()
    if not workflow_id:
        raise BadRequestError("workflow_id 不能为空")
    if len(workflow_id) > MAX_WORKFLOW_ID_LEN:
        raise BadRequestError(f"workflow_id 长度不能超过 {MAX_WORKFLOW_ID_LEN}，收到 {len(workflow_id)}")
    return workflow_id


def _node_targets(node: Dict[str, Any]) -> List[str]:
    """节点的出边目标（``condition`` 看 ``true_next`` / ``false_next``，其余看 ``next``）"""
    if node["type"] == "condition":
        return [target for target in (node.get("true_next"), node.get("false_next")) if target]
    target = node.get("next")
    return [target] if target else []


def _find_entry_node(nodes: List[Dict[str, Any]]) -> Optional[str]:
    """入度为 0 的入口节点 id（定义已校验通过时恰有一个）"""
    referenced: set = set()
    ids: List[str] = []
    for node in nodes:
        ids.append(node["id"])
        referenced.update(_node_targets(node))
    for node_id in ids:
        if node_id not in referenced:
            return node_id
    return None


def validate_definition(definition: Any) -> Dict[str, Any]:
    """校验工作流定义（纯函数），返回**归一化后的新 dict**

    规则（非法一律抛 ``BadRequestError`` 并说明原因）：

      - 必须是 JSON 对象，且含非空的 ``nodes`` 列表；
      - 每个节点必须是对象，``id`` 为非空字符串且**全局唯一**；
      - ``type`` 必须在 ``NODE_TYPES`` 里；
      - ``next`` / ``true_next`` / ``false_next`` 若给出（非 ``null``）必须指向**存在**的节点；
      - ``condition`` 节点必须同时给出 ``true_next`` 与 ``false_next`` 两个键；
      - 必须**恰好一个入口节点**（入度为 0）；
      - 有向图**不得有环**（DFS 检测）。
    """
    if not isinstance(definition, dict):
        raise BadRequestError("工作流定义必须是 JSON 对象")

    nodes = definition.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadRequestError("工作流定义必须包含非空的 nodes 列表")

    clean_nodes: List[Dict[str, Any]] = []
    node_map: Dict[str, Dict[str, Any]] = {}
    for index, raw_node in enumerate(nodes):
        if not isinstance(raw_node, dict):
            raise BadRequestError(f"第 {index} 个节点必须是 JSON 对象")
        node_id = raw_node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise BadRequestError(f"第 {index} 个节点缺少合法的 id")
        node_id = node_id.strip()
        if node_id in node_map:
            raise BadRequestError(f"节点 id 重复：{node_id}")
        node_type = raw_node.get("type")
        if node_type not in NODE_TYPES:
            raise BadRequestError(
                f"节点 {node_id} 的 type「{node_type}」非法（可选：{list(NODE_TYPES)}）"
            )
        if "config" in raw_node and not isinstance(raw_node["config"], dict):
            raise BadRequestError(f"节点 {node_id} 的 config 必须是 JSON 对象")
        node = dict(raw_node)
        node["id"] = node_id
        node_map[node_id] = node
        clean_nodes.append(node)

    id_set = set(node_map)

    # 边校验 + 入度收集
    referenced: set = set()
    for node in clean_nodes:
        node_id = node["id"]
        if node["type"] == "condition":
            for key in ("true_next", "false_next"):
                if key not in node:
                    raise BadRequestError(f"condition 节点 {node_id} 缺少 {key}")
        for key in ("next", "true_next", "false_next"):
            target = node.get(key)
            if target is None:
                continue
            if not isinstance(target, str) or target not in id_set:
                raise BadRequestError(
                    f"节点 {node_id} 的 {key} 指向不存在的节点「{target}」"
                )
            referenced.add(target)

    # 恰好一个入口节点
    entry_nodes = [node_id for node_id in node_map if node_id not in referenced]
    if len(entry_nodes) != 1:
        raise BadRequestError(
            f"工作流必须有且仅有一个入口节点（入度为 0），当前入口节点为 {entry_nodes or '无'}"
        )

    # 环检测（迭代式 DFS 三色法）
    adjacency: Dict[str, List[str]] = {node["id"]: _node_targets(node) for node in clean_nodes}
    white, grey, black = 0, 1, 2
    color: Dict[str, int] = {node_id: white for node_id in node_map}

    for start in node_map:
        if color[start] != white:
            continue
        color[start] = grey
        stack: List[Tuple[str, Any]] = [(start, iter(adjacency[start]))]
        while stack:
            node_id, children = stack[-1]
            advanced = False
            for child in children:
                if color[child] == grey:
                    raise BadRequestError(f"工作流定义存在环（{node_id} → {child} 回到已访问节点）")
                if color[child] == white:
                    color[child] = grey
                    stack.append((child, iter(adjacency[child])))
                    advanced = True
                    break
            if not advanced:
                color[node_id] = black
                stack.pop()

    normalized = dict(definition)
    normalized["nodes"] = clean_nodes
    return normalized


def _compare(actual: Any, op: str, expected: Any, var: str) -> bool:
    """受限比较（``==`` / ``!=`` 允许任意类型；大小比较要求同为数值且非 bool）"""
    if op == "==":
        return bool(actual == expected)
    if op == "!=":
        return bool(actual != expected)
    if isinstance(actual, bool) or isinstance(expected, bool):
        raise BadRequestError(f"变量「{var}」不支持布尔的大小比较")
    if not (isinstance(actual, (int, float)) and isinstance(expected, (int, float))):
        raise BadRequestError(
            f"变量「{var}」需要数值才能做「{op}」比较，收到 {type(actual).__name__}"
        )
    if op == ">":
        return actual > expected
    if op == ">=":
        return actual >= expected
    if op == "<":
        return actual < expected
    return actual <= expected  # op == "<="


def evaluate_condition(expression: Any, context: Dict[str, Any]) -> bool:
    """对受限条件表达式求值（纯函数）

    ``expression`` 形如 ``{"var": "count", "op": ">", "value": 10}``。运算符受限
    （``CONDITION_OPS``）；变量缺失 / 运算符不支持 / 类型不兼容一律抛
    ``BadRequestError``——刻意**不静默为 False**，否则条件节点会走错分支。
    """
    if not isinstance(expression, dict):
        raise BadRequestError("condition 节点的 config.expression 必须是 JSON 对象")
    var = expression.get("var")
    op = expression.get("op")
    if not isinstance(var, str) or not var:
        raise BadRequestError("condition 的 expression 缺少合法的 var")
    if op not in CONDITION_OPS:
        raise BadRequestError(f"不支持的比较运算符「{op}」（可选：{list(CONDITION_OPS)}）")
    if var not in context:
        raise BadRequestError(f"上下文中不存在变量「{var}」")
    return _compare(context[var], op, expression.get("value"), var)


def can_transition(current: Any, target: str) -> bool:
    """实例状态机：``current`` 是否可以转移到 ``target``（纯函数）"""
    if current == target:
        return False
    return target in ALLOWED_TRANSITIONS.get(str(current), frozenset())


def is_terminal_status(status: Any) -> bool:
    """``status`` 是否为终态（不可再流转）"""
    return status in TERMINAL_STATUSES


def _normalize_limit(limit: Any, *, default: int = 50, maximum: int = 500) -> int:
    """把 limit 归一化到 ``[1, maximum]``（非法取 ``default``）"""
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return min(value, maximum)


# ================================================================== 节点执行
async def _run_action(config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """执行 ``action`` 节点的内建动作（未知动作 → ``BadRequestError``）"""
    action = config.get("action")

    if action == "log":
        message = config.get("message")
        if not isinstance(message, str) or not message:
            raise BadRequestError("log 动作需要非空的 message")
        logger.info("工作流 log 动作：%s", message)
        return {"action": "log", "message": message}

    if action == "set_context":
        key = config.get("key")
        if not isinstance(key, str) or not key:
            raise BadRequestError("set_context 动作需要非空的 key")
        context[key] = config.get("value")
        return {"action": "set_context", "key": key, "value": context[key]}

    if action == "sleep":
        seconds = config.get("seconds", SLEEP_MIN_SECONDS)
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise BadRequestError("sleep 动作的 seconds 必须是数值")
        if not (SLEEP_MIN_SECONDS <= seconds <= SLEEP_MAX_SECONDS):
            raise BadRequestError(
                f"sleep 动作的 seconds 必须在 {SLEEP_MIN_SECONDS}~{SLEEP_MAX_SECONDS} 秒之间，收到 {seconds}"
            )
        await asyncio.sleep(seconds)
        return {"action": "sleep", "seconds": seconds}

    if action == "http_request":
        return await _run_http_request(config)

    raise BadRequestError(f"未知动作「{action}」（内建动作：{list(BUILTIN_ACTIONS)}）")


async def _run_http_request(config: Dict[str, Any]) -> Dict[str, Any]:
    """用 httpx 发一次**真实** HTTP 请求；4xx/5xx 视为动作失败"""
    url = config.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise BadRequestError("http_request 动作需要一个 http(s) 的 url")
    method = str(config.get("method") or "GET").upper()
    headers = config.get("headers") if isinstance(config.get("headers"), dict) else None
    params = config.get("params") if isinstance(config.get("params"), dict) else None
    json_body = config.get("json")
    raw_timeout = config.get("timeout", HTTP_TIMEOUT_SECONDS)
    if isinstance(raw_timeout, (int, float)) and not isinstance(raw_timeout, bool):
        timeout = float(raw_timeout)
    else:
        timeout = HTTP_TIMEOUT_SECONDS
    timeout = min(max(timeout, 0.1), 30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method, url, headers=headers, params=params, json=json_body
        )
    body = response.text[:HTTP_RESPONSE_MAX_CHARS]
    if response.status_code >= 400:
        raise BadRequestError(
            f"http_request 返回状态 {response.status_code}：{body[:200]}"
        )
    return {"action": "http_request", "status_code": response.status_code, "body": body}


def _node_runtime(node: Dict[str, Any]) -> Dict[str, Any]:
    """由定义节点派生一份运行期节点状态"""
    return {
        "node_id": node["id"],
        "node_type": node["type"],
        "config": dict(node.get("config") or {}),
        "status": "pending",
        "result": None,
        "started_at": None,
        "completed_at": None,
        "error": None,
    }


def _record(instance: Dict[str, Any], event: str, data: Dict[str, Any]) -> None:
    """向实例追加一条执行历史事件并刷新 ``updated_at``"""
    instance.setdefault("history", []).append(
        {"timestamp": _now_iso(), "event": event, "data": data}
    )
    instance["updated_at"] = _now_iso()


def _transition(instance: Dict[str, Any], target: str) -> None:
    """按状态机流转实例状态，非法转移抛 ``BadRequestError``"""
    current = instance.get("status")
    if not can_transition(current, target):
        raise BadRequestError(f"非法的状态流转：{current} → {target}")
    instance["status"] = target
    instance["updated_at"] = _now_iso()


# ================================================================== 服务
class WorkflowEngineService:
    """通用工作流引擎：定义管理 / 实例执行 / 审批 / 历史"""

    # -------------------------------------------------- 存储读写
    @staticmethod
    async def _get_setting_row(db: AsyncSession, key: str):
        from shared.models.system.system_settings import SystemSettings

        return (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == key).limit(1)
            )
        ).scalars().first()

    async def _load_json(self, db: AsyncSession, key: str, default: Any) -> Any:
        row = await self._get_setting_row(db, key)
        if row is None or not row.setting_value:
            return default
        try:
            return json.loads(row.setting_value)
        except ValueError:
            logger.warning("设置 %s 不是合法 JSON，按默认值处理：%s", key, (row.setting_value or "")[:80])
            return default

    async def _save_json(self, db: AsyncSession, key: str, value: Any, *, description: str) -> None:
        from shared.models.system.system_settings import SystemSettings

        row = await self._get_setting_row(db, key)
        now = datetime.now()
        payload = json.dumps(value, ensure_ascii=False)
        if row is None:
            db.add(
                SystemSettings(
                    setting_key=key,
                    setting_value=payload,
                    setting_type="json",
                    description=description,
                    is_public=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.setting_value = payload
            row.setting_type = "json"
            row.updated_at = now
        await db.commit()

    # -------------------------------------------------- 定义
    async def _load_definitions(self, db: AsyncSession) -> Dict[str, Any]:
        data = await self._load_json(db, DEFINITIONS_KEY, {})
        return data if isinstance(data, dict) else {}

    async def register_definition(
        self,
        db: AsyncSession,
        workflow_id: str,
        definition: Dict[str, Any],
        *,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """注册 / 覆盖一个工作流定义（先 ``validate_definition``，非法直接 400）"""
        workflow_id = validate_workflow_id(workflow_id)
        normalized = validate_definition(definition)
        normalized["workflow_id"] = workflow_id
        normalized["updated_at"] = _now_iso()
        normalized["updated_by"] = user_id

        definitions = await self._load_definitions(db)
        definitions[workflow_id] = normalized
        await self._save_json(db, DEFINITIONS_KEY, definitions, description="工作流定义集合")
        logger.info("注册工作流定义（%s，用户 %s，节点 %d）", workflow_id, user_id, len(normalized["nodes"]))
        return normalized

    async def list_definitions(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """列出全部工作流定义（按 workflow_id 升序）"""
        definitions = await self._load_definitions(db)
        return [definitions[key] for key in sorted(definitions)]

    async def get_definition(self, db: AsyncSession, workflow_id: str) -> Dict[str, Any]:
        """取单个工作流定义，不存在抛 ``NotFoundError``"""
        workflow_id = validate_workflow_id(workflow_id)
        definition = (await self._load_definitions(db)).get(workflow_id)
        if definition is None:
            raise NotFoundError(f"工作流定义不存在：{workflow_id}")
        return definition

    async def delete_definition(self, db: AsyncSession, workflow_id: str) -> None:
        """删除工作流定义，不存在抛 ``NotFoundError``"""
        workflow_id = validate_workflow_id(workflow_id)
        definitions = await self._load_definitions(db)
        if workflow_id not in definitions:
            raise NotFoundError(f"工作流定义不存在：{workflow_id}")
        definitions.pop(workflow_id)
        await self._save_json(db, DEFINITIONS_KEY, definitions, description="工作流定义集合")
        logger.info("删除工作流定义：%s", workflow_id)

    # -------------------------------------------------- 实例存储
    async def _load_instances(self, db: AsyncSession) -> List[Dict[str, Any]]:
        data = await self._load_json(db, INSTANCES_KEY, [])
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    async def _save_instances(self, db: AsyncSession, instances: List[Dict[str, Any]]) -> None:
        """落库实例数组，**最多保留最近 ``MAX_INSTANCES`` 条**（超出按 created_at 淘汰旧记录）"""
        ordered = sorted(instances, key=lambda item: str(item.get("created_at") or ""), reverse=True)
        trimmed = ordered[:MAX_INSTANCES]
        await self._save_json(db, INSTANCES_KEY, trimmed, description="工作流实例与执行记录")

    async def _persist(self, db: AsyncSession, instances: List[Dict[str, Any]], index: int,
                       instance: Dict[str, Any]) -> None:
        instances[index] = instance
        await self._save_instances(db, instances)

    async def _find_instance(self, db: AsyncSession, instance_id: str) -> Tuple[List[Dict[str, Any]], int]:
        instances = await self._load_instances(db)
        for index, item in enumerate(instances):
            if item.get("instance_id") == instance_id:
                return instances, index
        return instances, -1

    # -------------------------------------------------- 实例
    async def create_instance(self, db: AsyncSession, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> \
    Dict[str, Any]:
        """基于已注册的定义创建一个实例（状态 ``pending``）"""
        workflow_id = validate_workflow_id(workflow_id)
        definition = await self.get_definition(db, workflow_id)
        if context is None:
            context = {}
        if not isinstance(context, dict):
            raise BadRequestError("context 必须是 JSON 对象")

        node_defs = {node["id"]: node for node in definition["nodes"]}
        entry = _find_entry_node(definition["nodes"])
        instance_id = uuid.uuid4().hex
        now = _now_iso()
        instance: Dict[str, Any] = {
            "instance_id": instance_id,
            "workflow_id": workflow_id,
            "status": "pending",
            "context": dict(context),
            "current_node_id": entry,
            "awaiting_node": None,
            "nodes": {node_id: _node_runtime(node) for node_id, node in node_defs.items()},
            "history": [
                {"timestamp": now, "event": "created", "data": {"workflow_id": workflow_id, "context": dict(context)}}
            ],
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "error": None,
        }
        instances = await self._load_instances(db)
        instances.append(instance)
        await self._save_instances(db, instances)
        logger.info("创建工作流实例 %s（定义 %s）", instance_id, workflow_id)
        return instance

    async def execute(self, db: AsyncSession, instance_id: str) -> Dict[str, Any]:
        """驱动工作流实例逐节点执行（每步落库），返回执行后的实例"""
        instances, index = await self._find_instance(db, instance_id)
        if index < 0:
            raise NotFoundError(f"工作流实例不存在：{instance_id}")
        instance = instances[index]

        if instance.get("status") == STATUS_PENDING_APPROVAL:
            raise BadRequestError("实例正在等待审批，请先 approve 或 reject")
        if is_terminal_status(instance.get("status")):
            raise BadRequestError(f"实例已处于终态「{instance.get('status')}」，无法再次执行")

        definition = await self.get_definition(db, instance["workflow_id"])
        node_defs = {node["id"]: node for node in definition["nodes"]}

        if instance.get("status") == "pending":
            instance["current_node_id"] = instance.get("current_node_id") or _find_entry_node(definition["nodes"])
            _transition(instance, "running")
            await self._persist(db, instances, index, instance)

        return await self._run_loop(db, instances, index, node_defs)

    async def _execute_node(
        self, node_def: Dict[str, Any], runtime: Dict[str, Any], instance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行单个节点，返回 ``{result, next, awaiting}``（失败抛 ``BadRequestError``）"""
        node_type = node_def["type"]
        config = node_def.get("config") or {}
        context = instance["context"]

        if node_type == "action":
            result = await _run_action(config, context)
            return {"result": result, "next": node_def.get("next"), "awaiting": False}

        if node_type == "condition":
            condition_met = evaluate_condition(config.get("expression"), context)
            next_id = node_def["true_next"] if condition_met else node_def["false_next"]
            return {"result": {"condition_met": condition_met}, "next": next_id, "awaiting": False}

        if node_type == "approval":
            return {
                "result": {"approver": config.get("approver"), "awaiting": True},
                "next": None,
                "awaiting": True,
            }

        raise BadRequestError(f"未知节点类型「{node_type}」")

    async def _run_loop(
        self,
        db: AsyncSession,
        instances: List[Dict[str, Any]],
        index: int,
        node_defs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """从 ``current_node_id`` 起逐节点推进，直到结束 / 失败 / 停在审批"""
        instance = instances[index]
        while True:
            node_id = instance.get("current_node_id")
            if not node_id:
                _transition(instance, "completed")
                instance["completed_at"] = _now_iso()
                _record(instance, "completed", {})
                await self._persist(db, instances, index, instance)
                return instance

            node_def = node_defs.get(node_id)
            if node_def is None:
                message = f"节点 {node_id} 不存在于定义中"
                instance["error"] = message
                _transition(instance, "failed")
                instance["completed_at"] = _now_iso()
                _record(instance, "failed", {"node_id": node_id, "error": message})
                await self._persist(db, instances, index, instance)
                return instance

            runtime = instance["nodes"].get(node_id) or _node_runtime(node_def)
            instance["nodes"][node_id] = runtime
            runtime["status"] = "running"
            runtime["started_at"] = _now_iso()
            _record(instance, "node_started", {"node_id": node_id, "node_type": node_def["type"]})
            await self._persist(db, instances, index, instance)

            try:
                outcome = await self._execute_node(node_def, runtime, instance)
            except BadRequestError as exc:
                message = exc.msg
            except Exception as exc:  # noqa: BLE001 —— 任何节点内异常都要如实落库
                message = f"{type(exc).__name__}: {exc}"
            else:
                message = None

            if message is not None:
                runtime["status"] = "failed"
                runtime["error"] = message
                runtime["completed_at"] = _now_iso()
                instance["error"] = message
                _transition(instance, "failed")
                instance["completed_at"] = _now_iso()
                _record(instance, "failed", {"node_id": node_id, "error": message})
                await self._persist(db, instances, index, instance)
                return instance

            runtime["result"] = outcome["result"]
            runtime["completed_at"] = _now_iso()

            if outcome["awaiting"]:
                runtime["status"] = "waiting_approval"
                _record(instance, "node_finished", {"node_id": node_id, "result": outcome["result"]})
                _record(instance, "awaiting_approval", {"node_id": node_id})
                _transition(instance, STATUS_PENDING_APPROVAL)
                instance["awaiting_node"] = node_id
                instance["current_node_id"] = node_id
                await self._persist(db, instances, index, instance)
                return instance

            runtime["status"] = "completed"
            _record(instance, "node_finished", {"node_id": node_id, "result": outcome["result"]})
            instance["awaiting_node"] = None
            next_id = outcome.get("next")
            instance["current_node_id"] = next_id or None
            await self._persist(db, instances, index, instance)

    # -------------------------------------------------- 审批
    async def approve(
        self, db: AsyncSession, instance_id: str, *, comment: Optional[str] = None, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """通过当前审批节点并从其 ``next`` 继续执行"""
        return await self._resume_approval(db, instance_id, approved=True, comment=comment, user_id=user_id)

    async def reject(
        self, db: AsyncSession, instance_id: str, *, comment: Optional[str] = None, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """拒绝审批：实例置为 ``failed``（审批不通过是真实的失败，不是静默通过）"""
        return await self._resume_approval(db, instance_id, approved=False, comment=comment, user_id=user_id)

    async def _resume_approval(
        self,
        db: AsyncSession,
        instance_id: str,
        *,
        approved: bool,
        comment: Optional[str],
        user_id: Optional[int],
    ) -> Dict[str, Any]:
        instances, index = await self._find_instance(db, instance_id)
        if index < 0:
            raise NotFoundError(f"工作流实例不存在：{instance_id}")
        instance = instances[index]

        if instance.get("status") != STATUS_PENDING_APPROVAL:
            raise BadRequestError(f"实例当前状态「{instance.get('status')}」不可审批")

        node_id = instance.get("awaiting_node")
        runtime = instance["nodes"].get(node_id)
        if runtime is None:
            raise BadRequestError(f"实例等待的审批节点「{node_id}」不存在")

        runtime["completed_at"] = _now_iso()
        runtime["result"] = {
            "approved": approved,
            "approver": (runtime.get("config") or {}).get("approver"),
            "comment": comment,
            "operator_id": user_id,
        }
        instance["awaiting_node"] = None

        if not approved:
            runtime["status"] = "failed"
            runtime["error"] = "审批被拒绝"
            instance["error"] = "审批被拒绝"
            _transition(instance, "failed")
            instance["completed_at"] = _now_iso()
            _record(instance, "rejected", {"node_id": node_id, "comment": comment, "operator_id": user_id})
            await self._persist(db, instances, index, instance)
            return instance

        runtime["status"] = "completed"
        _record(instance, "approved", {"node_id": node_id, "comment": comment, "operator_id": user_id})
        _transition(instance, "running")

        definition = await self.get_definition(db, instance["workflow_id"])
        node_defs = {node["id"]: node for node in definition["nodes"]}
        node_def = node_defs.get(node_id, {})
        instance["current_node_id"] = node_def.get("next") or None
        await self._persist(db, instances, index, instance)
        return await self._run_loop(db, instances, index, node_defs)

    # -------------------------------------------------- 取消 / 查询
    async def cancel(self, db: AsyncSession, instance_id: str) -> Dict[str, Any]:
        """取消实例（终态实例不可取消）"""
        instances, index = await self._find_instance(db, instance_id)
        if index < 0:
            raise NotFoundError(f"工作流实例不存在：{instance_id}")
        instance = instances[index]
        if is_terminal_status(instance.get("status")):
            raise BadRequestError(f"实例已处于终态「{instance.get('status')}」，无法取消")
        _transition(instance, "cancelled")
        instance["awaiting_node"] = None
        instance["completed_at"] = _now_iso()
        _record(instance, "cancelled", {})
        await self._persist(db, instances, index, instance)
        logger.info("取消工作流实例：%s", instance_id)
        return instance

    async def get_instance(self, db: AsyncSession, instance_id: str) -> Dict[str, Any]:
        """取单个实例，不存在抛 ``NotFoundError``"""
        instances, index = await self._find_instance(db, instance_id)
        if index < 0:
            raise NotFoundError(f"工作流实例不存在：{instance_id}")
        return instances[index]

    async def list_instances(
        self, db: AsyncSession, *, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """列出实例（可按状态过滤），按创建时间倒序、截断到 ``limit``"""
        if status is not None and status not in (*INSTANCE_STATUS, STATUS_PENDING_APPROVAL):
            raise BadRequestError(f"未知实例状态「{status}」（可选：{[*INSTANCE_STATUS, STATUS_PENDING_APPROVAL]}）")
        size = _normalize_limit(limit)
        instances = await self._load_instances(db)
        if status is not None:
            instances = [item for item in instances if item.get("status") == status]
        instances.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return instances[:size]

    async def history(
        self, db: AsyncSession, *, instance_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """汇总执行历史事件（可按实例过滤），按时间倒序、截断到 ``limit``"""
        size = _normalize_limit(limit)
        instances = await self._load_instances(db)
        if instance_id is not None:
            instances = [item for item in instances if item.get("instance_id") == instance_id]
        events: List[Dict[str, Any]] = []
        for instance in instances:
            for event in instance.get("history") or []:
                if not isinstance(event, dict):
                    continue
                events.append(
                    {
                        "instance_id": instance.get("instance_id"),
                        "workflow_id": instance.get("workflow_id"),
                        "timestamp": event.get("timestamp"),
                        "event": event.get("event"),
                        "data": event.get("data"),
                    }
                )
        events.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        return events[:size]


#: 单例实例
workflow_engine_service = WorkflowEngineService()
