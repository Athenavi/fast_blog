/** 屏幕选项接口（/api/v3/system/screen-options，system 域）
 *
 * 后端契约逐条对齐 `src/api/v3/modules/system/screen_options/controller.py`（共 7 个端点）：
 *   GET    /system/screen-options                全部页面偏好，按 page 分组（**不补齐默认值**）
 *   GET    /system/screen-options/{page}         单页偏好（缺省项用 DEFAULT_OPTIONS 补齐）
 *   PUT    /system/screen-options/{page}         整体覆盖单页偏好（未知 page 自动新建）
 *   PATCH  /system/screen-options/{page}/{key}   修改单项（未知 page / key 自动新建）
 *   DELETE /system/screen-options/{page}/{key}   删除单项（不存在 → 404）
 *   DELETE /system/screen-options/{page}         删除整页（不存在 → 404）
 *   DELETE /system/screen-options                重置全部（返回被移除的页面数）
 *
 * 全部端点**只需登录**：操作对象恒为当前登录用户自己的偏好，接口不接受 `user_id`
 * 参数 —— 越权无处可传。`core/permission/codes.py` 里**不存在** `screen_options:*`
 * 权限码，故本模块沿用「无专属权限码的系统工具」惯例（同 maintenance / translation /
 * accessibility），由调用方取语义最近的 `module_system:setting:view` / `:edit`。
 *
 * 约束（对齐 service.py）：`page` 只允许 `[A-Za-z0-9_.-]`、长度 ≤ 64；
 * 选项键长度 ≤ 64；单页 ≤ 100 项；单值序列化 ≤ 8 KiB、整页 ≤ 16 KiB（超限返回 400）。
 *
 * 搬迁：本文件应放到 `src/api/modules/screenOptions.ts`；`import http from '../request'`
 * 在迁入后即指向 `src/api/request.ts`。若要在 `@/api` 聚合入口暴露 `screenOptionsApi`
 * 与类型，需父代理在 `src/api/index.ts` 追加导出（本次**未**改动该文件）。
 */

import http from '../request'

/** 单页选项：选项键 → 任意 JSON 可序列化值（可为 null） */
export type ScreenOptionsPageMap = Record<string, unknown>

/** 全部页面偏好：page → 该页选项（GET / 原样返回存储内容，不补齐默认值） */
export type ScreenOptionsAll = Record<string, ScreenOptionsPageMap>

/** DELETE / 的返回值：被移除的页面数 */
export interface ScreenOptionsResetResult {
  removed_pages: number
}

/**
 * 把 page / key 安全编入 URL 路径段。
 *
 * `page` 的合法字符集（字母 / 数字 / 下划线 / 点 / 连字符）本身无需编码，
 * 但选项键允许任意字符串（可能含空格 / 斜杠），必须编码以免污染路径分段。
 */
function seg(value: string): string {
  return encodeURIComponent(value)
}

export const screenOptionsApi = {
  /** 全部页面偏好（按 page 分组；原样存储内容，不做默认值补齐） */
  getAll: () => http.get<ScreenOptionsAll>('/system/screen-options'),

  /** 单页偏好（后端用 DEFAULT_OPTIONS 补齐缺省项后返回） */
  getPage: (page: string) =>
    http.get<ScreenOptionsPageMap>(`/system/screen-options/${seg(page)}`),

  /** 整体覆盖单页偏好（未知 page 自动新建）；返回落库后的该页选项 */
  setPage: (page: string, options: ScreenOptionsPageMap) =>
    http.put<ScreenOptionsPageMap>(`/system/screen-options/${seg(page)}`, options),

  /** 修改单页的某个选项（未知 page / key 自动新建）；返回该页更新后的全部选项 */
  patchOption: (page: string, key: string, value: unknown) =>
    http.patch<ScreenOptionsPageMap>(`/system/screen-options/${seg(page)}/${seg(key)}`, {value}),

  /** 删除单项（不存在 → 404）；返回该页剩余选项 */
  deleteOption: (page: string, key: string) =>
    http.delete<ScreenOptionsPageMap>(`/system/screen-options/${seg(page)}/${seg(key)}`),

  /** 删除整页偏好（不存在 → 404）；后端返回 data 为 null */
  deletePage: (page: string) =>
    http.delete<null>(`/system/screen-options/${seg(page)}`),

  /** 重置全部偏好（删除该用户的整行）；返回被移除的页面数 */
  resetAll: () => http.delete<ScreenOptionsResetResult>('/system/screen-options'),
}
