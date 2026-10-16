/**
 * 金额与币种格式化
 *
 * 为什么需要：后台商务页面此前把金额与币种**分开裸渲染**（`{{ amount }}` + 一个 `currency` span），
 * 于是同一个产品里出现三种写法：`99.9 USD`、`cny`（小写）、`¥100`——既没有千分位、
 * 也没有符号，币种大小写还互相矛盾（`payment.vue` 默认 `'USD'`，payment-gateway 插件默认 `'cny'`）。
 *
 * 这里统一走 `Intl.NumberFormat`：符号、小数位、千分位都按币种惯例来
 * （JPY/KRW 不带小数，CNY/USD 两位），并统一把币种代码规范成大写 ISO-4217。
 */

/** 站点默认币种：集中一处，便于后续接入站点设置（此前散落在页面里硬编码） */
export const DEFAULT_CURRENCY = 'USD'

/** 规范化币种代码：去空白 + 大写；非三位字母（ISO-4217）时回退 */
export function normalizeCurrency(code?: string | null, fallback = DEFAULT_CURRENCY): string {
  const value = String(code ?? '').trim().toUpperCase()
  return /^[A-Z]{3}$/.test(value) ? value : fallback
}

/**
 * 金额 + 币种符号（表格里推荐直接用这个，不要再单独渲染币种列）
 * 例：formatMoney(1234.5, 'cny') → ¥1,234.50
 */
export function formatMoney(
  amount?: number | null,
  currency?: string | null,
  locale = 'zh-CN',
): string {
  const value = Number(amount)
  if (amount === null || amount === undefined || !Number.isFinite(value)) return '-'
  const code = normalizeCurrency(currency)
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: code,
      currencyDisplay: 'narrowSymbol',
    }).format(value)
  } catch {
    // 极老的运行时缺该币种数据时的兜底
    return `${code} ${value.toFixed(2)}`
  }
}

/** 只格式化数值（千分位 + 固定小数位），用于已单独展示币种的场景 */
export function formatAmount(amount?: number | null, digits = 2, locale = 'zh-CN'): string {
  const value = Number(amount)
  if (amount === null || amount === undefined || !Number.isFinite(value)) return '-'
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}
