/**
 * 音频播放器工具（对应 astro 版 `AudioPlayer/helpers.ts`）
 *
 * 逐字歌词的逻辑与原来一致：中文按字、英文按词切分，再按当前行的时长比例
 * 计算高亮进度（卡拉 OK 效果）。
 */

export interface LyricLine {
  time: number
  text: string
}

/** 将歌词行拆分为逐字/逐词 token（中文按字，英文按单词，空格单独成 token） */
export function tokenizeText(text: string): string[] {
  const tokens: string[] = []
  let buf = ''
  for (const ch of text) {
    const isCJK = /[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/.test(ch)
    if (isCJK) {
      if (buf) {
        tokens.push(buf)
        buf = ''
      }
      tokens.push(ch)
    } else if (ch === ' ') {
      if (buf) {
        tokens.push(buf)
        buf = ''
      }
      tokens.push(' ')
    } else {
      buf += ch
    }
  }
  if (buf) tokens.push(buf)
  return tokens
}

/** 当前行的逐字高亮进度（0..1）；没有下一行时按 3 秒估算行长 */
export function calcKaraokeProgress(
  currentTime: number,
  lineStart: number,
  nextLineStart: number | null,
): number {
  const end = nextLineStart ?? lineStart + 3
  const duration = end - lineStart
  if (duration <= 0) return 1
  return Math.max(0, Math.min(1, (currentTime - lineStart) / duration))
}

/** 秒 → `m:ss` */
export function formatTime(time: number): string {
  if (!Number.isFinite(time) || time < 0) return '0:00'
  const minutes = Math.floor(time / 60)
  const seconds = Math.floor(time % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}
