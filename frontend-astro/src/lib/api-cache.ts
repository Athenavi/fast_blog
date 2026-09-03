/**
 * API 请求缓存工具
 * 支持内存缓存 + IndexedDB 持久化
 */

interface CacheEntry<T> {
    data: T;
    timestamp: number;
    ttl: number;
}

class ApiCache {
    private cache: Map<string, CacheEntry<any>> = new Map();
    private defaultTTL: number = 5 * 60 * 1000;
    private maxEntries: number = 200;
  private dbReady: Promise<IDBDatabase | null> | null = null;

    constructor(defaultTTL?: number, maxEntries?: number) {
      if (defaultTTL) this.defaultTTL = defaultTTL;
      if (maxEntries) this.maxEntries = maxEntries;
    }

    set<T>(key: string, data: T, ttl?: number): void {
      const entry: CacheEntry<T> = {data, timestamp: Date.now(), ttl: ttl || this.defaultTTL};
      this.cache.set(key, entry);
      this.persist(key, entry as CacheEntry<any>);

        // 限制缓存大小防止内存泄漏
        if (this.cache.size > this.maxEntries) {
            const oldest = this.cache.keys().next().value;
            if (oldest) this.cache.delete(oldest);
        }
    }

    delete(key: string): void {
        this.cache.delete(key);

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
        ttl?: number
    ): Promise<T> {
      // 1. Check memory cache
        const cached = this.get<T>(key);
        if (cached !== null) return cached;

      // 2. Check IndexedDB (for persisted data across sessions)
      const persisted = await this.loadFromDb<T>(key);
      if (persisted !== null) {
        // Restore to memory cache
        this.set(key, persisted, ttl);
        return persisted;
      }

      // 3. Fetch and cache
        const data = await fetchFn();
        this.set(key, data, ttl);
        return data;
    }

    get<T>(key: string): T | null {
        const entry = this.cache.get(key);
        if (!entry) return null;

        const now = Date.now();
        if (now - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return null;
        }
        return entry.data as T;
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
