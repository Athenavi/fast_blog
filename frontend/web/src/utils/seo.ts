/**
 * SEO 相关的小工具（前台）
 */

/**
 * 把资源地址补成**绝对 URL**。
 *
 * ## 为什么必须有这一步
 *
 * 后端的封面地址形如 `/api/v3/content/media/12/file`（相对路径，见
 * `content/media/service.py` 的 `media_file_url`）。而 `og:image` / `twitter:image`
 * 与 JSON-LD 的 `image` 按规范**必须是绝对 URL**：
 *
 *  - Open Graph / Twitter Card 的抓取器不解析相对路径 —— 实测行为是整张图被丢弃，
 *    于是文章分享到微信、X、Slack 时都是**没有配图的空卡片**；
 *  - 结构化数据里放相对地址同样无效，Google 的富媒体结果不会带图。
 *
 * 已经在用的 `og:url` / JSON-LD `url` 是拼了 `requestUrl.origin` 的，
 * 唯独图片漏了这一步，这里统一补上。
 *
 * 已是绝对地址（`http://`、`https://`、协议相对 `//`）或 `data:` 时原样返回 ——
 * 外链封面（第三方图床）不该被改写成本站地址。
 */
export function absoluteAssetUrl(
  value: string | null | undefined,
  origin: string,
): string | undefined {
  const raw = (value ?? '').trim()
  if (!raw) return undefined
  if (/^(?:https?:)?\/\//i.test(raw) || raw.startsWith('data:')) return raw

  const base = origin.replace(/\/+$/, '')
  if (!base) return raw
  return `${base}${raw.startsWith('/') ? '' : '/'}${raw}`
}
