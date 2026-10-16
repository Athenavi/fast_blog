/**
 * 行级差异比较（供文章版本对比用）
 *
 * ## 为什么手写而不装 `diff` / `jsdiff`
 *
 * 需求是"比较文章的两个版本"，粒度是**行**（Markdown 的段落/标题/列表项各占行），
 * 不需要字符级或词级 diff。LCS 的动态规划实现约几十行，无依赖、可读、可测；
 * 引入一个通用 diff 库只为这一个用途，成本高于收益。
 *
 * ## 算法
 *
 * 经典 LCS（最长公共子序列）DP + 回溯。复杂度 O(n·m)，对文章行数（数千行内）
 * 完全够用；**不做 Myers 优化**，因为优化带来的是常数级差异，而代码会难读得多。
 *
 * ## 为什么行号要单独算
 *
 * 前端展示 diff 时，左右两侧的行号**各自独立计数**（左侧是旧版本的行号，
 * 右侧是新版本的行号）。中间夹的"新增/删除"行不应该推进另一侧的行号 ——
 * 这一点算错，diff 的行号就会整体错位（GitHub 的 diff 视图也是这样分开计的）。
 */

export type DiffKind = 'equal' | 'add' | 'remove'

export interface DiffLine {
  kind: DiffKind
  /** 该行在**旧版本**中的行号（新增行为 null） */
  oldLine: number | null
  /** 该行在**新版本**中的行号（删除行为 null） */
  newLine: number | null
  text: string
}

export interface DiffStat {
  added: number
  removed: number
  unchanged: number
}

/** 按行切分。末尾换行不算作"多一个空行"。 */
function splitLines(text: string): string[] {
  if (!text) return []
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  // 末行是空的（文本以 \n 结尾）时丢掉，否则每次比较都会多出一条"删除空行"
  if (lines.length > 1 && lines[lines.length - 1] === '') lines.pop()
  return lines
}

/**
 * 计算两个文本的行级差异。
 *
 * 返回的序列可直接按顺序渲染成左右对照的 diff 视图。
 */
export function diffLines(oldText: string, newText: string): DiffLine[] {
  const a = splitLines(oldText ?? '')
  const b = splitLines(newText ?? '')

  // LCS 长度表：dp[i][j] = a[i..] 与 b[j..] 的最长公共子序列长度
  const dp: number[][] = Array.from({length: a.length + 1}, () => new Array<number>(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      dp[i]![j] = a[i] === b[j]
        ? (dp[i + 1]![j + 1] ?? 0) + 1
        : Math.max(dp[i + 1]![j] ?? 0, dp[i]![j + 1] ?? 0)
    }
  }

  const out: DiffLine[] = []
  let i = 0
  let j = 0
  let oldNo = 1
  let newNo = 1

  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      out.push({kind: 'equal', oldLine: oldNo++, newLine: newNo++, text: a[i]!})
      i++
      j++
    } else if ((dp[i + 1]![j] ?? 0) >= (dp[i]![j + 1] ?? 0)) {
      // 删旧 —— 只推进旧行号
      out.push({kind: 'remove', oldLine: oldNo++, newLine: null, text: a[i]!})
      i++
    } else {
      // 增新 —— 只推进新行号
      out.push({kind: 'add', oldLine: null, newLine: newNo++, text: b[j]!})
      j++
    }
  }
  while (i < a.length) out.push({kind: 'remove', oldLine: oldNo++, newLine: null, text: a[i++]!})
  while (j < b.length) out.push({kind: 'add', oldLine: null, newLine: newNo++, text: b[j++]!})

  return out
}

/** 差异统计（供侧边栏显示 +N −M） */
export function diffStat(lines: DiffLine[]): DiffStat {
  return lines.reduce<DiffStat>(
    (acc, line) => {
      if (line.kind === 'add') acc.added++
      else if (line.kind === 'remove') acc.removed++
      else acc.unchanged++
      return acc
    },
    {added: 0, removed: 0, unchanged: 0},
  )
}
