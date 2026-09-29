/** AI 技能框架接口（/api/v3/ai/skill，ai 域）
 *
 * 对齐后端 `src/api/v3/modules/ai/skill/controller.py`（4 个端点）：
 *   GET  /ai/skill             技能清单（可按分类 / 关键字过滤）
 *   GET  /ai/skill/categories  技能分类
 *   GET  /ai/skill/{name}      技能详情（含参数说明，供前端渲染表单）
 *   POST /ai/skill/{name}/run  执行技能（**真实执行**）
 *
 * 权限码：`module_ai:workflow:view`（查看）/ `module_ai:workflow:execute`（执行）。
 * 技能自身声明的 `required_permission` 会在执行时**再校验一次**（见
 * `registry._assert_permission`）——只给查看权的人不能借技能绕过写权限，
 * 因此前端把 `required_permission` 一并展示，便于管理员判断为何执行被拒。
 */

import http from '../request'

/** 技能参数声明（来自后端技能定义，如 `builtin.py` 的 `params=(...)`） */
export interface AiSkillParam {
  name: string
  /** 后端声明值，如 text / int */
  type: string
  required: boolean
  description?: string
  /** 可选默认值（键存在时才有） */
  default?: unknown
}

/** 一个技能（`registry.SkillRegistry._out` 的返回结构） */
export interface AiSkillItem {
  name: string
  label: string
  description: string
  category: string
  category_label: string
  /** 技能执行时额外校验的权限码；为 null 表示不额外要求 */
  required_permission?: string | null
  params: AiSkillParam[]
}

/** `GET /ai/skill` 返回体（后端固定包装 total + items） */
export interface AiSkillListResult {
  total: number
  items: AiSkillItem[]
}

/** 技能分类（`SKILL_CATEGORIES` 的键值对列表） */
export interface AiSkillCategory {
  category: string
  label: string
}

/** `POST /ai/skill/{name}/run` 请求体（schema.SkillRunRequest） */
export interface AiSkillRunPayload {
  /** 技能参数；键见技能详情的 params */
  params?: Record<string, unknown>
  /** 需要调用 LLM 的技能用它指定 AI 配置；留空后端取第一条 */
  config_id?: number | null
}

/** 技能执行结果（`registry.execute` 的返回结构） */
export interface AiSkillRunResult {
  skill: string
  label: string
  category: string
  duration_ms: number
  /** 技能处理器的原样返回值（形状由技能自己决定） */
  result: Record<string, unknown>
}

/** `GET /ai/skill` 的查询参数 */
export type AiSkillQuery = {
  category?: string
  keyword?: string
}

export const aiSkillApi = {
  /** 技能清单（可按分类 / 关键字过滤） */
  list: (params?: AiSkillQuery) => http.get<AiSkillListResult>('/ai/skill', params),

  /** 技能分类 */
  categories: () => http.get<AiSkillCategory[]>('/ai/skill/categories'),

  /** 技能详情（含参数说明） */
  detail: (name: string) => http.get<AiSkillItem>(`/ai/skill/${encodeURIComponent(name)}`),

  /** 执行技能（真实执行；技能内部会再校验它声明的权限） */
  run: (name: string, data: AiSkillRunPayload) =>
    http.post<AiSkillRunResult>(`/ai/skill/${encodeURIComponent(name)}/run`, data),
}
