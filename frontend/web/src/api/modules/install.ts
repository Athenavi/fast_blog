/** 安装自检接口（/api/v3/system/install，system 域）
 *
 * **只读且公开**：未安装的站点还没有管理员可用于鉴权，部署者必须能匿名自查。
 * 响应只含布尔位与版本号，不回传连接串 / 主机 / 路径细节。
 *
 * 初始化方式**按部署模式分流**（见下方 `installWizardApi`）：
 * `enterprise`（默认）不开放 Web 写口、走命令行；`single` 才开放 Web 安装向导。
 */

import http from '../request'

export interface InstallDatabaseCheck {
  ok: boolean
  /** 失败时只给异常类型名 */
  error?: string | null
}

export interface InstallMigrationCheck {
  /** 数据库里的 alembic_version */
  current?: string | null
  /** 代码里 alembic 脚本目录的 head */
  head?: string | null
  up_to_date: boolean
}

export interface InstallStatus {
  database: InstallDatabaseCheck
  migration: InstallMigrationCheck
  has_superuser: boolean
  installed: boolean
  /** pycrdt 是否可用（缺失只影响协同编辑，其余功能不受影响） */
  realtime_available: boolean
}

export const installApi = {
  /** 匿名可调（带了 token 也不会因此出错） */
  status: () => http.get<InstallStatus>('/system/install/status'),
}


// ── Web 安装向导（仅 DEPLOYMENT_MODE=single 且尚未安装时可用）──────────────
//
// 后端两道闸门：① 部署模式必须是 single；② 必须尚未安装（安装完成即永久关闭）。
// 前端只需读 `status()` 的 `available`，据此决定显示向导还是"请用命令行初始化"，
// 不需要自己去猜部署模式。

export interface WizardStep {
  key: string
  label: string
  description: string
}

export interface WizardStatus {
  /** single / enterprise */
  deployment_mode: string
  wizard_enabled: boolean
  installed: boolean
  /** 现在能否使用向导（= wizard_enabled 且未安装） */
  available: boolean
  steps: WizardStep[]
}

export interface WizardStepResult {
  success: boolean
  message: string
  /** 该步的非敏感细节（如环境检测的逐项结果） */
  detail?: Record<string, unknown> | null
}

export interface WizardDatabaseConfig {
  host: string
  port: number
  database: string
  username: string
  password: string
}

export interface WizardAdminConfig {
  username: string
  email: string
  password: string
}

export interface WizardSiteSettings {
  site_name: string
  site_url: string
  site_description: string
}

export const installWizardApi = {
  /** 匿名可调：部署模式 / 是否开放 / 是否可安装 / 步骤定义 */
  status: () => http.get<WizardStatus>('/system/install/wizard'),
  prerequisites: () =>
    http.post<WizardStepResult>('/system/install/wizard/prerequisites'),
  /** 先测连接、通了才写 .env（顺序由后端保证） */
  database: (config: WizardDatabaseConfig) =>
    http.post<WizardStepResult>('/system/install/wizard/database', config),
  migrate: () => http.post<WizardStepResult>('/system/install/wizard/migrate'),
  admin: (config: WizardAdminConfig) =>
    http.post<WizardStepResult>('/system/install/wizard/admin', config),
  settings: (config: WizardSiteSettings) =>
    http.post<WizardStepResult>('/system/install/wizard/settings', config),
  /** 种子 RBAC 并锁定安装状态 —— 之后向导写口永久关闭 */
  complete: () => http.post<WizardStepResult>('/system/install/wizard/complete'),
}
