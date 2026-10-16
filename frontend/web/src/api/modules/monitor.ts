/** 系统监控接口（/api/v3/system/monitor，system 域） */

import http from '../request'

export interface CpuInfo {
  count: number
  percent: number
  /** Windows 无 1/5/15 分钟负载，此时为空数组 */
  load_avg: number[]
}

export interface MemoryInfo {
  total: number
  used: number
  percent: number
}

export interface DiskInfo {
  device: string
  mountpoint: string
  fstype: string
  total: number
  used: number
  percent: number
}

export interface ProcessInfo {
  pid: number
  rss: number
  threads: number
}

export interface ServerInfo {
  platform: string
  hostname: string
  python_version: string
  boot_time: string
  uptime_seconds: number
  cpu: CpuInfo
  memory: MemoryInfo
  disks: DiskInfo[]
  process: ProcessInfo
}

export interface OnlineSession {
  id: number
  user_id: number
  device_info?: string | null
  ip_address?: string | null
  location?: string | null
  last_activity?: string | null
  created_at?: string | null
}

export interface OnlineStats {
  active_sessions: number
  recent_sessions: number
  unique_users: number
  window_seconds: number
}

export interface MonitorOverview {
  server: ServerInfo
  online: OnlineStats
}

export const monitorApi = {
  overview: () => http.get<MonitorOverview>('/system/monitor/overview'),
  server: () => http.get<ServerInfo>('/system/monitor/server'),
  onlineStats: () => http.get<OnlineStats>('/system/monitor/online/stats'),
  onlineList: (params?: { page?: number; page_size?: number }) =>
    http.page<OnlineSession>('/system/monitor/online', params),
  /** 强制下线（会话 ID） */
  kick: (sessionId: number) =>
    http.delete<{ session_id: number }>(`/system/monitor/online/${sessionId}`),
}
