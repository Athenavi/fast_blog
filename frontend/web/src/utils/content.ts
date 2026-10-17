/**
 * 从文章正文派生出的只读信息（编辑页用）
 *
 * 编辑页的大纲栏要实时显示「文里有哪几节、现在写到第几节」，元信息行要显示
 * 「多少字、读多久」。这两件事此前只在**阅读页**做过一遍 —— 那里是先渲染成
 * HTML、再用正则往 `<h2>/<h3>` 里塞 id（`components/site/ArticleDetailView.vue`）。
 *
 * 编辑页不能照抄那套：往 DOM 里塞 id 会污染 ProseMirror 的文档，协作（Yjs）与
 * 撤销栈都要跟着抖；而编辑态的滚动容器在后台布局是 `el-main`、在前台是 window，
 * 阅读页那套 `window` 滚动监听根本不触发。
 *
 * 所以这里统一用**序号**当大纲项的身份：目录项 `index` 对应正文容器里第 `index`
 * 个标题元素。不需要给任何节点加标识属性。
 *
 * ## 为什么一律从 Markdown 源码算，而不是从渲染结果算
 *
 * `useArticleForm` 存的正文**就是 Markdown**（编辑器是 CodeMirror 上的 Markdown 源码视图，
 * 中间没有文档树与序列化那一步）。大纲、字数、右侧的实时预览三者同读这一份字符串，
 * 就必然互相对得上；只要有一项改成从渲染结果现取，它和另外两项之间就多了一次
 * 「渲染是否忠实」的假设。
 * 顺带还免掉了编辑器实例浅响应带来的那套版本号计数器 —— 打一个字不会触发
 * `computed`，得自己造依赖源，而这恰好是最容易悄悄失效的那种代码。
 */

export interface OutlineItem {
  /** 在大纲中的序号，同时是正文里第 `index` 个标题元素的序号 */
  index: number
  /** 1~6 */
  level: number
  text: string
  /**
   * 这一行在 Markdown 源码里的起始偏移。
   *
   * 目录定位有两种世界：渲染结果里有真正的 `<h2>` 可以按序号找，源码里没有 ——
   * 只有「第 N 行以 `##` 开头」。留着这个偏移，两种世界都能按同一份目录跳过去，
   * 不必为源码模式再算一遍标题列表（两份必然分叉）。
   */
  offset: number
}

const HEADING_LINE = /^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$/
const FENCE_LINE = /^ {0,3}(`{3,}|~{3,})/

/**
 * 按行走一遍 Markdown，**跳过围栏代码块内部**，并把每行的起始偏移一起给出去。
 *
 * 抽成一个函数而不是两处各写一遍围栏状态机：`headingsFromMarkdown` 与
 * `stripMarkdown` 必须对「哪些行是代码」给出完全相同的判断，否则目录序号
 * 与字数会各自错位。
 *
 * 切行用 `split('\n')` 而不是 `/\r?\n/`：偏移要能加回来，`split(/\r?\n/)` 把 `\r`
 * 吞掉之后，行号与字符下标就对不上原文了。
 *
 * 闭栏按 CommonMark 规则：同类标记、长度不小于开栏才算闭合；
 * 到文末仍未闭合，则剩下的行全部按代码处理。
 */
function forEachProseLine(
  source: string,
  onLine: (line: string, offset: number) => void,
): void {
  let fenceChar = ''
  let fenceLength = 0
  let offset = 0

  for (const line of source.split('\n')) {
    const fence = FENCE_LINE.exec(line)
    const marker = fence?.[1]
    if (fence && marker) {
      const char = marker[0] ?? ''
      if (!fenceChar) {
        fenceChar = char
        fenceLength = marker.length
      } else if (char === fenceChar && marker.length >= fenceLength) {
        fenceChar = ''
        fenceLength = 0
      }
      offset += line.length + 1
      continue
    }
    if (!fenceChar) onLine(line, offset)
    offset += line.length + 1
  }
}

/**
 * 从 Markdown 源码取标题（编辑器与协作态的目录都读这份）。
 *
 * 必须跳过围栏代码块：一段示例脚本里的 `# 注释` 一旦进了目录，目录就出现点不到的
 * 条目 —— 源码里没有标题元素，序号会从这里开始整体错位。
 */
export function headingsFromMarkdown(source: string | null | undefined): OutlineItem[] {
  const items: OutlineItem[] = []
  forEachProseLine(source ?? '', (line, offset) => {
    const heading = HEADING_LINE.exec(line)
    const hashes = heading?.[1]
    const text = heading?.[2]?.trim()
    if (!hashes || !text) return
    items.push({index: items.length, level: hashes.length, text, offset})
  })
  return items
}

/**
 * 「字」的口径：中日韩按字符计，其它文字按词计。
 *
 * 用**码点区间**判断而不是正则字符类：区间写成十六进制才看得出彼此是否连续
 * （字符类里的区间错一位就静默漏掉整段文字，且肉眼看不出来）；而且这里本来
 * 就要逐字走一遍，顺带把词数一起数了，省掉两次全文扫描。
 */
const CJK_RANGES: ReadonlyArray<readonly [number, number]> = [
  [0x3040, 0x30ff], // 日文假名
  [0x3400, 0x4dbf], // 中日韩扩展 A
  [0x4e00, 0x9fff], // 中日韩基本汉字
  [0xac00, 0xd7af], // 谚文音节
  [0xf900, 0xfaff], // 兼容表意文字
]

function isCjk(code: number): boolean {
  for (const [from, to] of CJK_RANGES) {
    if (code >= from && code <= to) return true
  }
  return false
}

export interface ContentUnits {
  /** 字数（中日韩按字、西文按词） */
  units: number
  /** 预计阅读分钟数，至少 1 */
  minutes: number
}

/**
 * 字数与阅读时长。
 *
 * 入参是 Markdown 源码（`useArticleForm` 存的正是这个），所以要先剥掉标记 ——
 * 直接取 `length` 会把 `##`、`**`、反引号、图片链接的 URL 全算进字数，
 * 作者看到的数字比实际多出一截，而且随格式变化跳来跳去。
 */
export function countContentUnits(source: string | null | undefined): ContentUnits {
  const plain = stripMarkdown(source)
  let cjk = 0
  let words = 0
  let inWord = false

  // `for..of` 按码点迭代，代理对（emoji、生僻字）不会被拆成两个字符
  for (const char of plain) {
    if (isCjk(char.codePointAt(0) ?? 0)) {
      cjk += 1
      inWord = false
    } else if (!/\S/.test(char)) {
      inWord = false
    } else {
      if (!inWord) words += 1
      inWord = true
    }
  }

  const units = cjk + words
  return {units, minutes: Math.max(1, Math.round(units / 400))}
}

/** 行内标记：剥掉后不影响阅读的那几类符号 */
const INLINE_MARKS: ReadonlyArray<readonly [RegExp, string]> = [
  [/!\[([^\]]*)\]\([^)]*\)/g, '$1'], // 图片：留 alt
  [/\[([^\]]*)\]\([^)]*\)/g, '$1'], // 链接：留锚文本
  [/`{1,3}([^`]*)`{1,3}/g, '$1'], // 行内代码
  [/^[ ]{0,3}#{1,6}[ \t]+/gm, ''], // 标题井号
  [/^[ ]{0,3}>[ \t]?/gm, ''], // 引用
  [/^[ ]{0,3}(?:[-*+]|\d+[.)])[ \t]+/gm, ''], // 列表符号
  [/[*_~]{1,3}([^*_~]+)[*_~]{1,3}/g, '$1'], // 强调与删除线
]

/** 表格的分隔行（`| --- | --- |`）与竖线 */
const TABLE_DIVIDER = /^[ \t]*\|?[ \t:|-]+\|?[ \t]*\r?$/gm

/**
 * 把 Markdown 折成近似的纯文本。
 *
 * 只做「去掉不影响阅读的标记」这一件事，不追求完备 —— 这是给作者看的一个量级
 * 数字，不是排版引擎。代码块按整段丢弃处理（走 `forEachProseLine`），因为正文里
 * 它既不该计入字数，也不该被当成段落。
 */
export function stripMarkdown(source: string | null | undefined): string {
  const lines: string[] = []
  forEachProseLine(source ?? '', (line) => lines.push(line))

  let text = lines.join('\n')
  for (const [pattern, replacement] of INLINE_MARKS) {
    text = text.replace(pattern, replacement)
  }
  // 表格：分隔行整行丢掉，竖线换成空格（否则 `|` 会粘在词上，把两个词并成一个）
  return text.replace(TABLE_DIVIDER, ' ').replace(/\|/g, ' ').trim()
}
