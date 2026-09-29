/** 数据导出接口（`/api/v3/system/export/*`，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/export/controller.py`，共 3 个端点：
 *   GET  /system/export/templates        导出资源与字段清单（统一响应；入口权限 `module_analytics:report:view`）
 *   POST /system/export/preview          前 N 行 JSON 预览（统一响应；入口权限 + 资源细粒度权限）
 *   GET  /system/export/{resource}.csv   导出 CSV（**真实文件下载**，非统一响应包装；入口权限 + 资源细粒度权限）
 *
 * **权限分两层**（与后端一致）：
 *   - 入口权限：三个端点都要求 `module_analytics:report:view`（`codes.REPORT_VIEW`）；
 *   - 资源细粒度权限：导出 / 预览还会按该资源在 `EXPORT_RESOURCES` 登记的查看权限再校验一次
 *     （如导 `users` 需 `module_system:user:view`）。superuser 与通配码放行；权限加载失败一律
 *     fail-closed（403）。无权时后端返回 **403**，错误体 `msg` 形如「导出 users 需要权限 …」。
 *
 * **CSV 是真实文件流**：`Content-Disposition: attachment; filename="..."`，且带 `X-Export-Rows`
 * 记录导出行数。它不走 `{code,msg,data}` 信封，故不能用 `http.get`（`unwrap` 会误判），
 * 改用 `http.raw`（同一 axios 实例，已自动注入 Bearer token）+ `responseType: 'blob'`，
 * 再由本模块的 `downloadCsv` 触发浏览器下载。
 *
 * **Excel 导出未实现**（后端未安装 openpyxl，约定不引入新依赖），故只提供 CSV。
 */

import http from '../request'

/** 导出路径前缀（`http.raw` 的 baseURL 已是 `/api/v3`，此处省略该前缀） */
const EXPORT_BASE = '/system/export'

/** 字段定义：`key` 是**真实列名**，`label` 是中文表头（顺序即 CSV 列顺序） */
export interface ExportField {
  key: string
  label: string
}

/** 一种可导出资源（`GET /system/export/templates` 的 `resources[]` 元素） */
export interface ExportResource {
  /** 资源标识（用于预览 / 导出路径，如 `users` / `articles`） */
  resource: string
  /** 资源中文名 */
  label: string
  /** 该资源的细粒度查看权限码（导出 / 预览时会二次校验） */
  permission: string
  /** 字段清单 */
  fields: ExportField[]
}

/** `GET /system/export/templates` 的响应 `data` */
export interface ExportTemplatesResult {
  resources: ExportResource[]
  count: number
}

/** `POST /system/export/preview` 的请求体（对应后端 `ExportPreviewRequest`） */
export interface ExportPreviewRequest {
  /** 资源标识（见 `/export/templates`） */
  resource: string
  /** 预览行数（后端默认 20，范围 1~200） */
  limit?: number
  /** 关键词模糊过滤（命中资源的 `search_fields`） */
  keyword?: string | null
  /** 时间范围起点（含，ISO 时间；命中资源的 `time_field`） */
  start?: string | null
  /** 时间范围终点（含，ISO 时间；命中资源的 `time_field`） */
  end?: string | null
}

/** 预览的一行：键为**真实列名**，值为任意类型（含 null / bool / 时间字符串等） */
export type ExportRow = Record<string, unknown>

/** `POST /system/export/preview` 的响应 `data`（对应后端 `preview()` 返回值） */
export interface ExportPreviewResult {
  resource: string
  label: string
  /** 列定义（真实列名 + 中文表头） */
  columns: ExportField[]
  rows: ExportRow[]
  /** 实际返回行数 */
  count: number
}

/** `GET /system/export/{resource}.csv` 的查询参数（对应后端 `export_csv` 的 Query） */
export interface ExportCsvParams {
  /** 导出行数上限（后端默认 10000，范围 1~10000） */
  limit?: number
  keyword?: string | null
  start?: string | null
  end?: string | null
}

/** `downloadCsv` 的返回值：解析到的文件名与 `X-Export-Rows`（拿不到时为 null） */
export interface ExportDownloadResult {
  filename: string
  rows: number | null
}

/** 从 `Content-Disposition` 解析文件名：先 `filename*=UTF-8''`，再回退 `filename`，最后回退默认名 */
export function parseDispositionFilename(disposition: unknown, fallback: string): string {
  if (typeof disposition !== 'string' || !disposition) return fallback
  // 优先 RFC 5987 的 filename*=UTF-8''<pct-encoded>
  const starMatch = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (starMatch?.[1]) {
    try {
      const decoded = decodeURIComponent(starMatch[1].trim())
      if (decoded) return decoded
    } catch {
      /* 非法百分号编码：忽略，继续回退 */
    }
  }
  // 回退普通 filename="..." / filename=...
  const plainMatch = /filename="?([^";]+)"?/i.exec(disposition)
  if (plainMatch?.[1]) {
    const value = plainMatch[1].trim()
    if (value) return value
  }
  return fallback
}

/** 只带上真正有值的过滤参数（省略即用后端默认；null / 空串不发送） */
function buildQuery(params?: ExportCsvParams): Record<string, unknown> {
  const query: Record<string, unknown> = {}
  if (params?.limit != null) query.limit = params.limit
  if (params?.keyword) query.keyword = params.keyword
  if (params?.start) query.start = params.start
  if (params?.end) query.end = params.end
  return query
}

/** 从响应头里读 `X-Export-Rows`（导出行数），非数字或缺省时返回 null */
function readExportRows(headers: Record<string, unknown>): number | null {
  const raw = headers['x-export-rows']
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw
  if (typeof raw === 'string' && /^\d+$/.test(raw.trim())) return Number(raw.trim())
  return null
}

/**
 * 下载 CSV：`http.raw` 取 blob → 解析文件名 → 用临时 `<a download>` 触发浏览器下载。
 *
 * 只在浏览器环境触发下载（SSR 下仅返回文件名与行数）。`http.raw` 是同一 axios 实例，
 * baseURL 已是 `/api/v3`，故路径从 `/system/export` 起写。
 */
async function downloadCsv(
  resource: string,
  params?: ExportCsvParams,
): Promise<ExportDownloadResult> {
  const resp = await http.raw.get<Blob>(
    `${EXPORT_BASE}/${encodeURIComponent(resource)}.csv`,
    {params: buildQuery(params), responseType: 'blob'},
  )
  const headers = resp.headers as unknown as Record<string, unknown>
  const filename = parseDispositionFilename(headers['content-disposition'], `${resource}.csv`)
  const rows = readExportRows(headers)

  if (import.meta.client) {
    const blob =
      typeof Blob !== 'undefined' && resp.data instanceof Blob
        ? resp.data
        : new Blob([resp.data as BlobPart])
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = filename
    anchor.style.display = 'none'
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(objectUrl)
  }

  return {filename, rows}
}

export const systemExportApi = {
  /** 导出资源与字段清单（`module_analytics:report:view`） */
  templates: () => http.get<ExportTemplatesResult>(`${EXPORT_BASE}/templates`),

  /** 前 N 行 JSON 预览（入口权限 + 资源细粒度权限；无权时 403） */
  preview: (data: ExportPreviewRequest) =>
    http.post<ExportPreviewResult>(`${EXPORT_BASE}/preview`, data),

  /** 导出 CSV 真实文件（入口权限 + 资源细粒度权限；无权时 403），触发浏览器下载 */
  downloadCsv,
}
