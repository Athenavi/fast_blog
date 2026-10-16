/** 进程监督接口（/api/v3/ops/supervisor，ops 域）
 *
 * 后端边界（页面必须如实呈现，不得掩盖）：
 *  - 登记项存在 `system_settings` 的 `supervisor.config`，**无独立表**；
 *  - 状态由三层健康检查（pid 存活 / 端口 / HTTP）判定，进程生命周期归部署层；
 *  - 启停/重启**只执行登记过的命令**（API 不接受任意命令串），需 `confirm=true`；
 *  - 未登记该动作 / 未在运行 / 探测失败都会**如实回报原因**，不会假装成功。
 */

import http from '../request'

/** 三层健康检查配置（未配置的层跳过并在 detail 里说明） */
export interface SupervisorHealthConfig {
  host: string
  /** 端口监听检查；null 表示未配置 */
  port?: number | null
  /** HTTP 端点检查；null 表示未配置 */
  url?: string | null
}

/** 一个被托管的进程登记项（PUT 提交用；不含探测结果） */
export interface SupervisorProcessPayload {
  name: string
  description?: string | null
  start_command?: string | null
  stop_command?: string | null
  restart_command?: string | null
  /** 可选：读 pid 采指标（项目根内相对路径） */
  pid_file?: string | null
  /** 必须在 logs/ 或 storage/logs/ 下 */
  log_file?: string | null
  health: SupervisorHealthConfig
  is_active: boolean
}

/** 三层探测结果；未配置的层为 null */
export interface SupervisorProbe {
  healthy: boolean
  alive?: boolean | null
  port_open?: boolean | null
  http_ok?: boolean | null
  /** 逐层说明（含“未配置 / 读不到 pid”等如实原因） */
  detail: string[]
}

/** 进程指标；无 pid 或 psutil 缺失时 available=false 并带 detail */
export interface SupervisorMetrics {
  available: boolean
  detail?: string | null
  cpu_percent?: number | null
  memory_rss_mb?: number | null
  threads?: number | null
  uptime_seconds?: number | null
  create_time?: number | null
}

/** 登记项 + 实时探测（GET 列表用） */
export interface SupervisorProcess extends SupervisorProcessPayload {
  probe: SupervisorProbe
  metrics: SupervisorMetrics
}

/** GET / PUT `/ops/supervisor/process` 响应体 */
export interface SupervisorConfig {
  processes: SupervisorProcess[]
  total: number
  updated_at?: string | null
  /** 保存时被拒绝的项（校验失败原因）；保存成功时为空数组 */
  issues: string[]
}

/** 单进程三层健康检查结果 */
export interface SupervisorHealth {
  process: string
  healthy: boolean
  alive?: boolean | null
  port_open?: boolean | null
  http_ok?: boolean | null
  detail: string[]
}

/** 日志读取结果（只允许 logs/ 与 storage/logs/ 下的文件） */
export interface SupervisorLog {
  available: boolean
  detail?: string | null
  path?: string | null
  total_lines: number
  lines: string[]
}

/** 启停 / 重启动作 */
export type SupervisorAction = 'start' | 'stop' | 'restart'

/** 动作结果；`ok=false` 时 `detail` 写明原因（不会静默） */
export interface SupervisorActionResult {
  ok: boolean
  action: string
  process: string
  command?: string | null
  returncode?: number | null
  duration_ms?: number | null
  detail: string
  output?: string | null
}

export const supervisorApi = {
  /** 登记项 + 实时探测（状态 / 健康 / 指标） */
  list: () => http.get<SupervisorConfig>('/ops/supervisor/process'),

  /** 整体替换登记；校验不通过时后端**不落库**并返回 issues */
  save: (processes: SupervisorProcessPayload[]) =>
    http.put<SupervisorConfig>('/ops/supervisor/process', {processes}),

  /** 三层健康检查（只读） */
  health: (name: string) =>
    http.get<SupervisorHealth>(`/ops/supervisor/process/${encodeURIComponent(name)}/health`),

  /** 日志末尾 N 行 */
  log: (name: string, lines = 200) =>
    http.get<SupervisorLog>(`/ops/supervisor/process/${encodeURIComponent(name)}/log`, {lines}),

  /** 启动 / 停止 / 重启（真实执行部署命令，固定带 confirm=true；失败会在结果里带原因） */
  act: (name: string, action: SupervisorAction) =>
    http.post<SupervisorActionResult>(
      `/ops/supervisor/process/${encodeURIComponent(name)}/${action}`,
      {confirm: true},
    ),
}
