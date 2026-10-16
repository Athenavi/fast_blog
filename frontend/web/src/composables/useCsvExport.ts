import dayjs from 'dayjs'

/**
 * CSV 导出
 *
 * 后台有 20+ 个数据表格（文章、用户、支付流水、日志、报表…），此前没有任何导出途径，
 * 运营/财务只能对着屏幕手抄。这里提供一个通用实现：调用方给出列定义与"取数函数"，
 * 由调用方决定导出范围（通常是"当前筛选条件下的全部结果"，而不是当前页那 20 行）。
 *
 * 两个容易踩的细节都已处理：
 *  - Excel 打开 UTF-8 CSV 必须带 BOM，否则中文全是乱码；
 *  - 单元格里的逗号/引号/换行必须按 RFC 4180 转义。
 */
export interface CsvColumn<T> {
  /** 取哪个字段 */
  key: string
  /** 表头文案（已翻译好的字符串） */
  label: string
  /** 自定义取值（默认直接取 `row[key]`，null/undefined 输出空串） */
  format?: (row: T) => string | number | null | undefined
}

export interface UseCsvExportOptions<T> {
  /** 文件名（不含扩展名与时间戳） */
  filename: string
  columns: CsvColumn<T>[]
  /** 取数：通常是"按当前筛选条件拉全量"，由调用方保证不与界面状态脱节 */
  rows: () => Promise<T[]> | T[]
}

export function useCsvExport<T extends object>(options: UseCsvExportOptions<T>) {
  const exporting = ref(false)
  const failed = ref(false)

  function escapeCell(value: unknown): string {
    const text = value === null || value === undefined ? '' : String(value)
    return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }

  function build(rows: T[]): string {
    const header = options.columns.map((column) => escapeCell(column.label)).join(',')
    const body = rows.map((row) =>
      options.columns
        .map((column) =>
          escapeCell(column.format ? column.format(row) : (row as Record<string, unknown>)[column.key]),
        )
        .join(','),
    )
    return [header, ...body].join('\r\n')
  }

  async function exportCsv(): Promise<boolean> {
    if (exporting.value) return false
    exporting.value = true
    failed.value = false
    try {
      const rows = await options.rows()
      const blob = new Blob([`\uFEFF${build(rows)}`], {type: 'text/csv;charset=utf-8'})
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${options.filename}-${dayjs().format('YYYYMMDD-HHmm')}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      return true
    } catch {
      failed.value = true
      return false
    } finally {
      exporting.value = false
    }
  }

  return {exporting, failed, exportCsv}
}
