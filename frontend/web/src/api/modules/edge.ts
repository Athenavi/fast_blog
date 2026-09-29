/** 边缘函数接口（`/api/v3/system/edge`，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/edge/controller.py`，共 7 个端点：
 *   - GET    /function                    函数列表（可选 ?path= 预览路由命中）
 *   - POST   /function                    注册函数
 *   - GET    /function/{name}             函数详情（含源码）
 *   - DELETE /function/{name}             删除函数
 *   - POST   /function/{name}/validate    代码静态校验 + 产物摘要
 *   - POST   /function/{name}/deploy      部署（无凭据时如实返回未部署）
 *   - GET    /function/{name}/log         本地操作 / 部署日志
 *
 * 权限（`src/api/v3/core/permission/codes.py`）：
 *   - 查看：`module_system:integration:view`
 *   - 注册：`module_system:integration:create`
 *   - 校验 / 部署：`module_system:integration:edit`
 *   - 删除：`module_system:integration:delete`
 *
 * **安全语义（如实呈现，不得美化）**：后端**从不执行**用户提交的代码
 * （`service.py` 全程无 eval / exec / subprocess）；`validate` / `deploy` 只做静态检查
 * （体积 / 禁用 API / 入口契约）+ 生成产物摘要。缺少平台凭据时 `deploy` 返回
 * `deployed=false` + `reason` + 需要配置的环境变量清单，**绝不伪造「已部署」**。
 *
 * 说明：列表端点**不是分页**结构（`data` 为 `{total, items}`、无 `pagination`），
 * 因此一律用 `http.get` 而非 `http.page`。
 */

import http from '../request'

/** 边缘平台标准名（`service.PLATFORM_*`；别名已在后端规范化） */
export type EdgePlatform = 'cloudflare_workers' | 'vercel_edge'

/** 注册函数的请求体（`schema.EdgeFunctionCreate`） */
export interface EdgeFunctionCreate {
  /** 函数名：字母开头，可含字母 / 数字 / 下划线 / 连字符，长度 1..100 */
  name: string
  /** 平台名，见 {@link EdgePlatform}（别名由后端规范化） */
  platform: string
  /** 路由：精确路径（`/api/edge/hello`）或以 `*` 结尾的前缀通配（`/blog/*`） */
  route: string
  /** 源码；留空则部署平台自带的转发模板 */
  code?: string
  /** 边缘缓存秒数，0 表示不缓存（0..86400） */
  cache_ttl?: number
  description?: string
  /** 是否参与路由匹配 */
  enabled?: boolean
}

/** 函数详情（`service._detail`：完整定义，含源码） */
export interface EdgeFunctionDetail {
  name: string
  platform: string
  route: string
  code: string
  cache_ttl: number
  description: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

/** 列表中的函数摘要（`service._summary`：不含源码，附体积信息） */
export interface EdgeFunctionSummary {
  name: string
  platform: string
  route: string
  cache_ttl: number
  description: string
  enabled: boolean
  created_at?: string
  updated_at?: string
  /** 源码字节数 */
  code_bytes: number
  /** 是否使用了自定义源码（false = 部署平台转发模板） */
  has_custom_code: boolean
}

/** 列表响应（`service.list_functions`）；请求带 `path` 时附 `match` */
export interface EdgeFunctionListResult {
  total: number
  items: EdgeFunctionSummary[]
  /** 仅当请求带 `path` 时存在：命中的函数名（无命中为 null） */
  match?: { path: string; function: string | null }
}

/** 单条静态校验项（`service.validate_code` 的 checks / errors / warnings 元素） */
export interface EdgeValidationCheck {
  rule: string
  severity: string
  message: string
}

/** 静态校验结果（`service.validate_code`） */
export interface EdgeValidationResult {
  valid: boolean
  platform: string
  byte_size: number
  size_limit: number
  errors: EdgeValidationCheck[]
  warnings: EdgeValidationCheck[]
  checks: EdgeValidationCheck[]
  summary: { errors: number; warnings: number }
}

/** 产物文件条目（`service.build_artifact` 的 files 元素） */
export interface EdgeArtifactFile {
  path: string
  role: string
  bytes: number
  sha256: string
}

/** 将要部署的产物摘要（`service.build_artifact`；**不写盘、不执行**） */
export interface EdgeArtifact {
  platform: string
  label: string
  name: string
  route: string
  cache_ttl: number
  entry: string
  entry_bytes: number
  entry_sha256: string
  files: EdgeArtifactFile[]
  total_bytes: number
  executed: boolean
  note: string
}

/** 平台凭据状态（`service.credential_status`；只读环境变量，**不含明文**） */
export interface EdgeCredentialStatus {
  platform: string
  available: boolean
  env: Record<string, boolean>
  required_env: string[]
}

/** 注册函数响应（`service.create_function`） */
export interface EdgeCreateResult {
  function: EdgeFunctionDetail
  validation: EdgeValidationResult
  artifact: EdgeArtifact
}

/** 校验响应（`service.validate_function`） */
export interface EdgeValidateResult {
  name: string
  platform: string
  /** 是否使用了临时覆盖代码（编辑器场景） */
  overridden: boolean
  validation: EdgeValidationResult
  artifact: EdgeArtifact
  credentials: EdgeCredentialStatus
}

/** 部署响应（`service.deploy_function`） */
export interface EdgeDeployResult {
  name: string
  platform: string
  route: string
  artifact: EdgeArtifact
  /** 代码是否通过静态校验 */
  validated: boolean
  /** 是否真的部署成功；无凭据 / 校验不过时**一律**为 false */
  deployed: boolean
  /** 未部署的原因（原样展示，如「未配置平台凭据」「代码校验未通过」） */
  reason?: string | null
  /** 校验未通过时附带 */
  validation?: EdgeValidationResult
  /** 存在凭据检查时附带 */
  credentials?: EdgeCredentialStatus
  /** 无凭据时的提示（需配置的环境变量） */
  hint?: string
  /** 部署成功时的平台返回信息 */
  remote?: Record<string, unknown>
}

/** 部署记录条目（`service._record_deployment` 写入的动态字段，各 mode 字段略有差异） */
export interface EdgeDeployLogEntry {
  name?: string
  platform?: string
  at?: string
  deployed?: boolean
  /** rejected / skipped / remote_error / remote */
  mode?: string
  reason?: string | null
  checksum?: string
  bytes?: number
  remote?: Record<string, unknown> | null
}

/** 日志响应（`service.log_function`；只含**本地记录**，非真实边缘运行日志） */
export interface EdgeLogResult {
  name: string
  platform?: string | null
  /** 恒定 "local" */
  source: string
  /** 恒定 false：未接入远端日志 */
  remote: boolean
  /** 说明为何没有真实远端日志（原样展示） */
  reason?: string
  deployment_count: number
  entries: EdgeDeployLogEntry[]
}

export const edgeApi = {
  /** 函数列表；`path` 用于预览某路径会命中哪个函数 */
  listFunctions: (path?: string) =>
    http.get<EdgeFunctionListResult>('/system/edge/function', path ? {path} : undefined),

  /** 注册函数（写入 `system_settings.edge.functions`；同名会返回 400） */
  createFunction: (data: EdgeFunctionCreate) =>
    http.post<EdgeCreateResult>('/system/edge/function', data),

  /** 函数详情（含源码） */
  getFunction: (name: string) =>
    http.get<EdgeFunctionDetail>(`/system/edge/function/${name}`),

  /** 删除函数 */
  deleteFunction: (name: string) =>
    http.delete<null>(`/system/edge/function/${name}`),

  /** 静态校验：`code` 传值则校验临时（未保存）代码，省略则校验已保存定义 */
  validateFunction: (name: string, code?: string | null) =>
    http.post<EdgeValidateResult>(
      `/system/edge/function/${name}/validate`,
      code == null ? undefined : {code},
    ),

  /** 部署（无凭据时返回 `deployed=false` + `reason`，不伪造成功） */
  deployFunction: (name: string) =>
    http.post<EdgeDeployResult>(`/system/edge/function/${name}/deploy`),

  /** 本地操作 / 部署日志（最近 `limit` 条，1..200） */
  logFunction: (name: string, limit?: number) =>
    http.get<EdgeLogResult>(
      `/system/edge/function/${name}/log`,
      limit != null ? {limit} : undefined,
    ),
}
