/** 维护模式接口（`/api/v3/system/maintenance`，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/maintenance/controller.py`（任务 14c），共 9 个端点：
 *   GET    /system/maintenance/status       维护状态（**公开**）
 *   GET    /system/maintenance/config       读取配置（`module_system:setting:view`）
 *   PUT    /system/maintenance/config       保存配置（`module_system:setting:edit`）
 *   POST   /system/maintenance/enable       开启（`module_system:setting:edit`）
 *   POST   /system/maintenance/disable      关闭（`module_system:setting:edit`）
 *   PUT    /system/maintenance/message      改提示语（`module_system:setting:edit`）
 *   POST   /system/maintenance/schedule     设定时窗口（`module_system:setting:edit`）
 *   POST   /system/maintenance/whitelist    加白名单 IP（`module_system:setting:edit`）
 *   DELETE /system/maintenance/whitelist/{ip} 移除白名单 IP（`module_system:setting:edit`）
 *
 * 「是否生效」由后端**纯计算**（`src/api/v3/modules/system/maintenance/service.py: evaluate`）：
 * `enabled`（人工开关）或 `in_schedule`（当前时间落在定时窗口内）取或，且请求 IP 不在白名单。
 * 写操作会主动失效中间件缓存（`src/middleware/maintenance_mode.py: invalidate_cache`），
 * 开关立即生效 —— 前端无需自行判断，一律以 `status` 返回为准。
 */

import http from '../request'

/** 维护模式配置（`GET/PUT /system/maintenance/config`，字段与后端 `DEFAULT_CONFIG` 一致） */
export interface MaintenanceConfig {
  /** 人工开关 */
  enabled: boolean
  /** 503 页面提示语（默认「系统正在维护中，请稍后访问」） */
  message: string
  /** 维护期间仍可访问的 IP 列表 */
  whitelist_ips: string[]
  /** 定时窗口开始（ISO 时间；未设置时为 null） */
  scheduled_start: string | null
  /** 定时窗口结束（ISO 时间；未设置时为 null） */
  scheduled_end: string | null
  /** 503 正文 `retry_after` 与响应头 `Retry-After`（秒） */
  retry_after: number
}

/** 维护状态（`GET /system/maintenance/status`，公开；针对**当前请求 IP** 计算） */
export interface MaintenanceStatus {
  /** 是否对当前 IP 生效：`(enabled 或 in_schedule) 且 未命中白名单` */
  active: boolean
  /** 人工开关 */
  enabled: boolean
  /** 当前时间是否落在定时窗口内 */
  in_schedule: boolean
  /** 当前请求 IP 是否在白名单中 */
  whitelisted: boolean
  /** 展示给访客的提示语 */
  message: string
  /** 建议访客重试间隔（秒） */
  retry_after: number
  scheduled_start: string | null
  scheduled_end: string | null
  whitelist_ips: string[]
  /** 本次状态计算时间（ISO） */
  checked_at: string
}

/** `PUT /system/maintenance/config` 请求体：只接受 `DEFAULT_CONFIG` 已知键，未知键后端会 400 */
export interface MaintenanceConfigPayload {
  enabled?: boolean
  message?: string
  whitelist_ips?: string[]
  scheduled_start?: string | null
  scheduled_end?: string | null
  retry_after?: number
}

/** `POST /system/maintenance/enable` 请求体（全部可省略，省略即不覆盖） */
export interface MaintenanceEnablePayload {
  /** 覆盖提示语（≤500 字） */
  message?: string
  /** 覆盖白名单 */
  whitelist_ips?: string[]
  /** 覆盖 Retry-After（0 ~ 604800 秒） */
  retry_after?: number
}

/** `POST /system/maintenance/schedule` 请求体 */
export interface MaintenanceSchedulePayload {
  /** ISO 时间 */
  scheduled_start: string
  /** ISO 时间，须晚于 `scheduled_start` */
  scheduled_end: string
  /** 可选：一并覆盖提示语 */
  message?: string
}

export const maintenanceApi = {
  /** 维护状态（**公开**，无需权限；前台据此渲染维护页与倒计时） */
  status: () => http.get<MaintenanceStatus>('/system/maintenance/status'),

  /** 读取配置（`module_system:setting:view`） */
  getConfig: () => http.get<MaintenanceConfig>('/system/maintenance/config'),

  /** 保存配置（`module_system:setting:edit`；未知键 / 非法时间 / 非法 retry_after 会 400） */
  saveConfig: (data: MaintenanceConfigPayload) =>
    http.put<MaintenanceConfig>('/system/maintenance/config', data),

  /** 开启维护模式（`module_system:setting:edit`；可顺便覆盖提示语 / 白名单 / Retry-After） */
  enable: (data: MaintenanceEnablePayload = {}) =>
    http.post<MaintenanceConfig>('/system/maintenance/enable', data),

  /** 关闭维护模式（`module_system:setting:edit`） */
  disable: () => http.post<MaintenanceConfig>('/system/maintenance/disable'),

  /** 修改维护提示语（`module_system:setting:edit`；1 ~ 500 字，空串后端会拒绝） */
  updateMessage: (message: string) =>
    http.put<MaintenanceConfig>('/system/maintenance/message', {message}),

  /** 设定时维护窗口（`module_system:setting:edit`；到点自动生效 / 失效） */
  schedule: (data: MaintenanceSchedulePayload) =>
    http.post<MaintenanceConfig>('/system/maintenance/schedule', data),

  /** 加入 IP 白名单（`module_system:setting:edit`；重复会 400） */
  addWhitelist: (ip: string) => http.post<MaintenanceConfig>('/system/maintenance/whitelist', {ip}),

  /** 移出 IP 白名单（`module_system:setting:edit`；不存在会 400） */
  removeWhitelist: (ip: string) =>
    http.delete<MaintenanceConfig>(`/system/maintenance/whitelist/${encodeURIComponent(ip)}`),
}
