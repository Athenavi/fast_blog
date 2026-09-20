/** 安装自检接口（/api/v3/system/install，system 域）
 *
 * **只读且公开**：未安装的站点还没有管理员可用于鉴权，部署者必须能匿名自查；
 * 后端刻意**没有**任何 setup / 初始化写口（初始化一律走命令行脚本）。
 * 响应只含布尔位与版本号，不回传连接串 / 主机 / 路径细节。
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
