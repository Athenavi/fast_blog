/**
 * API 请求缓存工具
 * 支持内存缓存 + IndexedDB 持久化 + LRU淘汰策略 + 请求去重 + 缓存预热
 */

interface CacheEntry<T> {
    data: T;
    timestamp: number;
    ttl: number;
  // LRU: 最后访问时间
  lastAccess: number;
  // LRU: 访问次数
  hitCount: number;
}

interface CacheStats {
  size: number;
  hits: number;
  misses: number;
  hitRate: number;
  evictions: number;
}

class ApiCache {
  // 使用 Ordered Map 实现 LRU（按最后访问时间排序）
    private cache: Map<string, CacheEntry<any>> = new Map();
    private defaultTTL: number = 5 * 60 * 1000;
    private maxEntries: number = 200;
  private maxMemoryBytes: number = 5 * 1024 * 1024; // 5MB memory limit
  private dbReady: Promise<IDBDatabase | null> | null = null;

  // 请求去重：进行中的请求 Promise 缓存
  private pendingRequests: Map<string, Promise<any>> = new Map();

  // 缓存统计
  private stats = {hits: 0, misses: 0, evictions: 0};

    constructor(defaultTTL?: number, maxEntries?: number) {
      if (defaultTTL) this.defaultTTL = defaultTTL;
      if (maxEntries) this.maxEntries = maxEntries;
    }

    set<T>(key: string, data: T, ttl?: number): void {
      const now = Date.now();
      const existing = this.cache.get(key);
      const entry: CacheEntry<T> = {
        data,
        timestamp: now,
        lastAccess: now,
        hitCount: existing?.hitCount || 0,
        ttl: ttl || this.defaultTTL
      };
      this.cache.set(key, entry);

      // 如果在后台持久化失败不影响主流程
      this.persist(key, entry as CacheEntry<any>).catch(() => {
      });

      // LRU淘汰：超出容量时淘汰最不常用条目
      while (this.cache.size > this.maxEntries) {
        this.evictLRU();
      }

      // 内存限制检查
      this.checkMemoryLimit();
    }

  /** 清理所有过期条目 */
  cleanupExpired(): number {
    const now = Date.now();
    let cleaned = 0;
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key);
        cleaned++;
      }
    }
    return cleaned;
    }

    delete(key: string): void {
        this.cache.delete(key);
      this.pendingRequests.delete(key);

      // Also delete from IndexedDB
      if (typeof indexedDB !== 'undefined') {
        this.getDb().then(db => {
          if (!db) return;
          try {
            const tx = db.transaction('api', 'readwrite');
            tx.objectStore('api').delete(key);
          } catch {
          }
        });
      }
    }

    clear(): void {
        this.cache.clear();
      this.pendingRequests.clear();
      this.stats = {hits: 0, misses: 0, evictions: 0};

      if (typeof indexedDB !== 'undefined') {
        this.getDb().then(db => {
          if (!db) return;
          try {
            const tx = db.transaction('api', 'readwrite');
            tx.objectStore('api').clear();
          } catch {
          }
        });
      }
    }

    async getOrFetch<T>(
        key: string,
        fetchFn: () => Promise<T>,
        ttl?: number,
        options?: { dedupe?: boolean; staleWhileRevalidate?: boolean }
    ): Promise<T> {
      const dedupe = options?.dedupe ?? true;
      const staleWhileRevalidate = options?.staleWhileRevalidate ?? false;

      // 1. Check memory cache
      const cached = this.get<T>(key, staleWhileRevalidate);
      if (cached !== null) {
        this.stats.hits++;

        // 后台静默更新（stale-while-revalidate）
        if (staleWhileRevalidate && this.isStale(key)) {
          this.fetchAndCache(key, fetchFn, ttl).catch(() => {
          });
        }
        return cached;
      }
      this.stats.misses++;

      // 2. 请求去重：如果相同请求已在进行中，返回同一个 Promise
      if (dedupe && this.pendingRequests.has(key)) {
        return this.pendingRequests.get(key) as Promise<T>;
      }

      // 3. Check IndexedDB (for persisted data across sessions)
      const persisted = await this.loadFromDb<T>(key);
      if (persisted !== null) {
        // Restore to memory cache
        this.set(key, persisted, ttl);
        return persisted;
      }

      // 4. Fetch and cache (with deduplication)
      const promise = this.fetchAndCache(key, fetchFn, ttl);
      if (dedupe) {
        this.pendingRequests.set(key, promise);
      }
      try {
        const data = await promise;
        return data;
      } finally {
        if (dedupe) {
          this.pendingRequests.delete(key);
        }
      }
    }

  get<T>(key: string, ignoreTTL?: boolean): T | null {
        const entry = this.cache.get(key);
        if (!entry) return null;

        const now = Date.now();
    if (!ignoreTTL && now - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return null;
        }

    // 更新 LRU 信息
    entry.lastAccess = now;
    entry.hitCount++;

        return entry.data as T;
    }

  /** 获取缓存统计信息 */
  getStats(): CacheStats {
    const total = this.stats.hits + this.stats.misses;
    return {
      size: this.cache.size,
      hits: this.stats.hits,
      misses: this.stats.misses,
      hitRate: total > 0 ? this.stats.hits / total : 0,
      evictions: this.stats.evictions,
    };
  }

  /** 预热缓存：批量预加载关键数据 */
  async warmup<T>(entries: Array<{ key: string; fetchFn: () => Promise<T>; ttl?: number }>): Promise<void> {
    // 使用 requestIdleCallback 在空闲时预加载
    const idleLoad = () => {
      Promise.all(entries.map(async ({key, fetchFn, ttl}) => {
        if (!this.has(key)) {
          return this.getOrFetch(key, fetchFn, ttl, {dedupe: true});
        }
      })).catch(() => {
      });
    };

    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(idleLoad, {timeout: 2000});
    } else {
      idleLoad();
    }
  }

  /** LRU淘汰：访问最少且最旧的条目 */
  private evictLRU(): void {
    let minAccess = Infinity;
    let minKey: string | null = null;

    for (const [key, entry] of this.cache.entries()) {
      // 综合评分：访问时间权重70% + 访问次数权重30%
      const score = entry.lastAccess + (Math.max(0, 1000 - entry.hitCount) * 1000);
      if (score < minAccess) {
        minAccess = score;
        minKey = key;
      }
    }

    if (minKey) {
      this.cache.delete(minKey);
      this.stats.evictions++;

      // 同步删除 IndexedDB
      if (typeof indexedDB !== 'undefined') {
        this.getDb().then(db => {
          if (!db) return;
          try {
            const tx = db.transaction('api', 'readwrite');
            tx.objectStore('api').delete(minKey);
          } catch {
          }
        });
      }
    }
  }

  /** 内存限制检查：估算缓存内存占用，超限时强制清理 */
  private checkMemoryLimit(): void {
    if (typeof performance === 'undefined') return;
    const mem = (performance as any).memory;
    if (!mem) return;

    // 如果JS堆占用接近限制，清理过期条目
    const usageRatio = mem.usedJSHeapSize / mem.totalJSHeapSize;
    if (usageRatio > 0.8) {
      this.cleanupExpired();
    }
  }

  /** 统一的获取+缓存逻辑 */
  private async fetchAndCache<T>(
    key: string,
    fetchFn: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
        const data = await fetchFn();
        this.set(key, data, ttl);
        return data;
    }

  /** 检查缓存是否存在但已过期（用于 stale-while-revalidate） */
  private isStale(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;
    return Date.now() - entry.timestamp > entry.ttl * 0.8; // 80% TTL 后视为 stale
  }

  /** Initialize IndexedDB */
  private getDb(): Promise<IDBDatabase | null> {
    if (this.dbReady) return this.dbReady;
    if (typeof indexedDB === 'undefined') {
      this.dbReady = Promise.resolve(null);
      return this.dbReady;
    }

    this.dbReady = new Promise((resolve) => {
      try {
        const request = indexedDB.open('fastblog-cache', 1);
        request.onupgradeneeded = (event) => {
          const db = (event.target as IDBOpenDBRequest).result;
          if (!db.objectStoreNames.contains('api')) {
            db.createObjectStore('api', {keyPath: 'key'});
          }
        };
        request.onsuccess = (event) => {
          resolve((event.target as IDBOpenDBRequest).result);
        };
        request.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });

    return this.dbReady;
  }

  /** Persist to IndexedDB */
  private async persist(key: string, entry: CacheEntry<any>): Promise<void> {
    const db = await this.getDb();
    if (!db) return;

    try {
      const tx = db.transaction('api', 'readwrite');
      tx.objectStore('api').put({key, ...entry});
    } catch {
      // Silent fail - cache is optional
    }
  }

    has(key: string): boolean {
        const entry = this.cache.get(key);
        if (!entry) return false;

        const now = Date.now();
        if (now - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return false;
        }
        return true;
    }

  /** Load from IndexedDB */
  private async loadFromDb<T>(key: string): Promise<T | null> {
    const db = await this.getDb();
    if (!db) return null;

    return new Promise((resolve) => {
      try {
        const tx = db.transaction('api', 'readonly');
        const request = tx.objectStore('api').get(key);
        request.onsuccess = () => {
          const record = request.result;
          if (record) {
            const entry = record as any;
            if (Date.now() - entry.timestamp < entry.ttl) {
              resolve(entry.data as T);
            } else {
              resolve(null);
            }
          } else {
            resolve(null);
          }
        };
        request.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
    }
}

export const apiCache = new ApiCache();

export async function cachedFetch<T>(
    url: string,
    options?: RequestInit,
    ttl?: number
): Promise<T> {
    const cacheKey = `${url}:${JSON.stringify(options || {})}`;

    return apiCache.getOrFetch(
        cacheKey,
        async () => {
            if (!url || typeof url !== 'string') {
                throw new Error(`Invalid URL: ${url}`);
            }

            const response = await fetch(url, options);

            if (response.status === 304) {
                const cachedData = apiCache.get<T>(cacheKey);
                if (cachedData !== null) return cachedData;
                throw new Error('304 Not Modified but no cached data available');
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const text = await response.text();
            if (!text) throw new Error('Empty response from server');

            try {
                return JSON.parse(text) as T;
            } catch (e) {
                throw new Error(`Failed to parse JSON response: ${e instanceof Error ? e.message : 'Unknown error'}`);
            }
        },
        ttl
    );
}

export function clearCacheByPattern(pattern: string): void {
    const keysToDelete: string[] = [];
    for (const key of apiCache['cache'].keys()) {
        if (key.includes(pattern)) {
            keysToDelete.push(key);
        }
    }
    keysToDelete.forEach(key => apiCache.delete(key));
}
