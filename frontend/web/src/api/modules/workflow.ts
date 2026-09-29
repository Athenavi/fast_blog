/** 通用工作流引擎接口（`/api/v3/system/workflow`，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/workflow/controller.py`，共 13 个端点：
 *   - 定义：列表 / 注册（覆盖）/ 只校验 / 单个 / 删除
 *   - 实例：创建 / 列表 / 单个 / 逐步执行 / 通过审批 / 拒绝审批 / 取消
 *   - 历史：汇总执行事件
 *
 * 权限（`src/api/v3/core/permission/codes.py`）：查看用 `module_system:setting:view`，
 * 写入 / 执行用 `module_system:setting:edit`（`SETTING_VIEW` / `SETTING_EDIT`）。
 *
 * 存储落 `system_settings`：定义存键 `workflow.definitions`（`{workflow_id: definition}`），
 * 实例与执行记录存键 `workflow.instances`（数组，最多保留最近 200 条）。定义结构由后端
 * `service.validate_definition` 做权威校验（非法一律 400），前端只做 JSON 合法性把关。
 *
 * 说明：定义 / 实例 / 历史列表端点**不是分页**结构（`data` 为数组、无 `pagination`），
 * 实例与历史用 `limit` 而非 `page` / `page_size`，故一律用 `http.get` 而非 `http.page`。
 */

import http from '../request'

/** 节点类型（`service.NODE_TYPES`） */
export type WorkflowNodeType = 'action' | 'condition' | 'approval'

/** 实例状态（`service.INSTANCE_STATUS` + 运行期态 `pending_approval`） */
export type WorkflowInstanceStatus =
  | 'pending'
  | 'running'
  | 'pending_approval'
  | 'completed'
  | 'failed'
  | 'cancelled'

/** 节点执行状态（实例内单个节点的运行期 status） */
export type WorkflowNodeRuntimeStatus =
  | 'pending'
  | 'running'
  | 'waiting_approval'
  | 'completed'
  | 'failed'

/**
 * 定义中的一个节点（`validate_definition` 归一化后的形状）。
 *
 * - `action` 节点：`config.action` ∈ `log` / `set_context` / `http_request` / `sleep`，出边看 `next`
 * - `condition` 节点：`config.expression` = `{var, op, value}`，出边看 `true_next` / `false_next`
 * - `approval` 节点：`config.approver` 可选，出边看 `next`
 */
export interface WorkflowNode {
  id: string
  type: WorkflowNodeType | string
  config?: Record<string, unknown>
  /** 普通 / 审批节点的后继 */
  next?: string | null
  /** condition 为真时的后继 */
  true_next?: string | null
  /** condition 为假时的后继 */
  false_next?: string | null
}

/** 一个注册后的工作流定义（`definition` 本身附加了 workflow_id / updated_at / updated_by） */
export interface WorkflowDefinition {
  workflow_id?: string
  nodes: WorkflowNode[]
  updated_at?: string
  updated_by?: number | null

  [key: string]: unknown
}

/** `POST /definition` 请求体（`schema.WorkflowDefinitionSave`） */
export interface WorkflowDefinitionSave {
  /** 工作流标识（唯一），1~100 字符 */
  workflow_id: string
  /** 工作流定义：至少含 `nodes` 列表 */
  definition: Record<string, unknown>
}

/** `POST /definition/validate` 请求体（`schema.WorkflowDefinitionValidate`） */
export interface WorkflowDefinitionValidate {
  /** 待校验的工作流定义 */
  definition: Record<string, unknown>
}

/** `POST /definition/validate` 的成功返回（只校验不保存；失败直接 400） */
export interface WorkflowValidationResult {
  /** 恒定 true —— 非法定义会抛 400 而非返回 false */
  valid: boolean
  /** 归一化后定义内自带的 workflow_id（原始定义未提供时为 null） */
  workflow_id?: string | null
  nodes: WorkflowNode[]
}

/** `POST /instance` 请求体（`schema.WorkflowInstanceCreate`） */
export interface WorkflowInstanceCreate {
  /** 已注册的工作流标识 */
  workflow_id: string
  /** 实例上下文变量 */
  context?: Record<string, unknown>
}

/** `POST /instance/{id}/approve|reject` 请求体（`schema.WorkflowApproval`，可空） */
export interface WorkflowApproval {
  /** 审批意见，≤500 字 */
  comment?: string | null
}

/** 实例内单个节点的运行期状态 */
export interface WorkflowNodeRuntime {
  node_id: string
  node_type: string
  config: Record<string, unknown>
  status: WorkflowNodeRuntimeStatus | string
  result: unknown
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
}

/** 一条执行历史事件 */
export interface WorkflowHistoryEvent {
  timestamp: string
  /** created / node_started / node_finished / awaiting_approval / approved / rejected / failed / completed / cancelled */
  event: string
  data: Record<string, unknown> | null
}

/** 一个工作流实例（`create_instance` / `execute` / `approve` … 的返回） */
export interface WorkflowInstance {
  instance_id: string
  workflow_id: string
  status: WorkflowInstanceStatus | string
  context: Record<string, unknown>
  current_node_id?: string | null
  /** 停在审批时的节点 id */
  awaiting_node?: string | null
  nodes: Record<string, WorkflowNodeRuntime>
  history: WorkflowHistoryEvent[]
  created_at: string
  updated_at: string
  completed_at?: string | null
  error?: string | null
}

/** `GET /history` 汇总出的一条事件（附实例 / 定义标识） */
export interface WorkflowHistoryItem {
  instance_id?: string | null
  workflow_id?: string | null
  timestamp?: string | null
  event?: string | null
  data?: Record<string, unknown> | null
}

/**
 * 实例列表查询参数（对齐后端 `status` / `limit` query）。
 *
 * 用 `type` 而非 `interface`：对象字面量类型可赋给 `Record<string, unknown>`
 * （`http.get` 的 params 类型），`interface` 无隐式索引签名会被拒。
 */
export type WorkflowInstanceQuery = {
  /** 按状态过滤，如 running / pending_approval */
  status?: string
  /** 返回条数上限（1~500） */
  limit?: number
}

/** 历史查询参数（`type` 理由同上） */
export type WorkflowHistoryQuery = {
  /** 只看某个实例的历史 */
  instance_id?: string
  limit?: number
}

export const workflowApi = {
  // ------------------------------------------------------------ 定义
  /** 工作流定义列表（按 workflow_id 升序，不分页） */
  listDefinitions: () => http.get<WorkflowDefinition[]>('/system/workflow/definition'),

  /** 注册 / 覆盖一个工作流定义（非法定义返回 400 并说明原因） */
  registerDefinition: (workflowId: string, definition: Record<string, unknown>) =>
    http.post<WorkflowDefinition>('/system/workflow/definition', {
      workflow_id: workflowId,
      definition,
    }),

  /** 只校验工作流定义（不保存；非法时抛出后端错误） */
  validateDefinition: (definition: Record<string, unknown>) =>
    http.post<WorkflowValidationResult>('/system/workflow/definition/validate', {definition}),

  /** 单个工作流定义（不存在抛 404） */
  getDefinition: (workflowId: string) =>
    http.get<WorkflowDefinition>(`/system/workflow/definition/${encodeURIComponent(workflowId)}`),

  /** 删除工作流定义（不存在抛 404） */
  deleteDefinition: (workflowId: string) =>
    http.delete<null>(`/system/workflow/definition/${encodeURIComponent(workflowId)}`),

  // ------------------------------------------------------------ 实例
  /** 基于已注册的定义创建实例（初始状态 pending） */
  createInstance: (workflowId: string, context: Record<string, unknown> = {}) =>
    http.post<WorkflowInstance>('/system/workflow/instance', {
      workflow_id: workflowId,
      context,
    }),

  /** 实例列表（可按状态过滤，按创建时间倒序） */
  listInstances: (params?: WorkflowInstanceQuery) =>
    http.get<WorkflowInstance[]>('/system/workflow/instance', params),

  /** 单个实例（不存在抛 404） */
  getInstance: (instanceId: string) =>
    http.get<WorkflowInstance>(`/system/workflow/instance/${encodeURIComponent(instanceId)}`),

  /** 逐步执行实例（遇到审批节点停在 pending_approval） */
  execute: (instanceId: string) =>
    http.post<WorkflowInstance>(`/system/workflow/instance/${encodeURIComponent(instanceId)}/execute`),

  /** 通过审批并从审批节点的 next 继续执行 */
  approve: (instanceId: string, comment?: string) =>
    http.post<WorkflowInstance>(`/system/workflow/instance/${encodeURIComponent(instanceId)}/approve`, {
      comment: comment ?? null,
    }),

  /** 拒绝审批（实例置为 failed） */
  reject: (instanceId: string, comment?: string) =>
    http.post<WorkflowInstance>(`/system/workflow/instance/${encodeURIComponent(instanceId)}/reject`, {
      comment: comment ?? null,
    }),

  /** 取消实例（终态实例不可取消） */
  cancel: (instanceId: string) =>
    http.post<WorkflowInstance>(`/system/workflow/instance/${encodeURIComponent(instanceId)}/cancel`),

  // ------------------------------------------------------------ 历史
  /** 汇总执行历史事件（可按实例过滤，按时间倒序） */
  history: (params?: WorkflowHistoryQuery) =>
    http.get<WorkflowHistoryItem[]>('/system/workflow/history', params),
}
