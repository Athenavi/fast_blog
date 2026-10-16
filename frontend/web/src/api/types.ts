/**
 * v3 统一响应契约（与后端 src/api/v3/common/response.py 保持一致）
 *
 * 后端返回：{ code, msg, data, pagination }
 *   - code === 200 表示成功
 *   - 分页列表的 data 是数组，分页信息在同级 pagination
 */

export interface Pagination {
  page: number
  page_size: number
  total: number
  pages: number
}

export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data: T
  pagination: Pagination | null
}

/** 分页列表的统一结构（由 request.page() 组装） */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  pages: number
}

/** 分页查询参数（与后端 PageQuery 对齐） */
export interface PageQuery {
  page?: number
  page_size?: number
  keyword?: string
  order_by?: string
  order?: 'asc' | 'desc'

  [key: string]: unknown
}

export const CODE_SUCCESS = 200
