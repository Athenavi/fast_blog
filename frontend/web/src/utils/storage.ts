/** localStorage 轻封装（带 JSON 序列化与异常兜底） */

export const storage = {
  get<T = string>(key: string, fallback: T | null = null): T | null {
    try {
      const raw = localStorage.getItem(key)
      if (raw === null) return fallback
      try {
        return JSON.parse(raw) as T
      } catch {
        return raw as unknown as T
      }
    } catch {
      return fallback
    }
  },

  set(key: string, value: unknown): void {
    try {
      localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value))
    } catch {
      // 隐私模式或容量超限时忽略
    }
  },

  remove(key: string): void {
    try {
      localStorage.removeItem(key)
    } catch {
      // ignore
    }
  },

  clear(keys: string[]): void {
    keys.forEach((key) => this.remove(key))
  },
}
