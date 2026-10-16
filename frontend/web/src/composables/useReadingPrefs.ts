/**
 * 阅读偏好（正文字号 / 行宽）
 *
 * 为什么值得做：正文宽度与字号此前是写死的（`max-w-read` + 固定字号），
 * 读者没有任何调节余地——长文阅读里这是最常被抱怨的一点。
 *
 * 与主题偏好一致：用 cookie 存（SSR 首屏就带上正确的 class，不闪），
 * 因此同一份偏好在服务端渲染与客户端接管之间保持一致。
 */
export type ReadingFontSize = 'sm' | 'md' | 'lg'
export type ReadingWidth = 'narrow' | 'wide'

export const FONT_SIZES: Array<{ label: string; value: ReadingFontSize }> = [
  {label: 'fontSmall', value: 'sm'},
  {label: 'fontMedium', value: 'md'},
  {label: 'fontLarge', value: 'lg'},
]

export const WIDTHS: Array<{ label: string; value: ReadingWidth }> = [
  {label: 'widthNarrow', value: 'narrow'},
  {label: 'widthWide', value: 'wide'},
]

const FONT_CLASS: Record<ReadingFontSize, string> = {
  sm: 'text-[15px] leading-[1.8]',
  md: 'text-[17px] leading-[1.85]',
  lg: 'text-[19px] leading-[1.9]',
}

export function useReadingPrefs() {
  const fontSize = useCookie<ReadingFontSize>('fb-read-size', {
    default: () => 'md',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
  })
  const width = useCookie<ReadingWidth>('fb-read-width', {
    default: () => 'narrow',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
  })

  const fontSizeClass = computed(() => FONT_CLASS[fontSize.value] ?? FONT_CLASS.md)
  const widthClass = computed(() => (width.value === 'wide' ? 'max-w-3xl' : 'max-w-read'))

  return {fontSize, width, fontSizeClass, widthClass}
}
