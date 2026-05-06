/**
 * API 请求缓存工具
 * 用于缓存 API 响应，减少重复请求
 */

interface CacheEntry<T> {
    data: T;
    timestamp: number;
    ttl: number; // Time to live in milliseconds
}

class ApiCache {
    private cache: Map<string, CacheEntry<any>> = new Map();
    private defaultTTL: number = 5 * 60 * 1000; // 5 minutes default

    constructor(defaultTTL?: number) {
        if (defaultTTL) {
            this.defaultTTL = defaultTTL;
        }
    }

    /**
     * Get cached data if available and not expired
     */
    get<T>(key: string): T | null {
        const entry = this.cache.get(key);

        if (!entry) {
            return null;
        }

        const now = Date.now();
        if (now - entry.timestamp > entry.ttl) {
            // Cache expired
            this.cache.delete(key);
            return null;
        }

        return entry.data as T;
    }

    /**
     * Set cache data with TTL
     */
    set<T>(key: string, data: T, ttl?: number): void {
        this.cache.set(key, {
            data,
            timestamp: Date.now(),
            ttl: ttl || this.defaultTTL
        });
    }

    /**
     * Remove specific cache entry
     */
    delete(key: string): void {
        this.cache.delete(key);
    }

    /**
     * Clear all cache
     */
    clear(): void {
        this.cache.clear();
    }

    /**
     * Check if cache entry exists and is valid
     */
    has(key: string): boolean {
        const entry = this.cache.get(key);

        if (!entry) {
            return false;
        }

        const now = Date.now();
        if (now - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return false;
        }

        return true;
    }

    /**
     * Get or fetch data with caching
     */
    async getOrFetch<T>(
        key: string,
        fetchFn: () => Promise<T>,
        ttl?: number
    ): Promise<T> {
        const cached = this.get<T>(key);
        if (cached !== null) {
            return cached;
        }

        const data = await fetchFn();
        this.set(key, data, ttl);
        return data;
    }
}

// Create a global instance
export const apiCache = new ApiCache();

// Helper function for cached fetch
export async function cachedFetch<T>(
    url: string,
    options?: RequestInit,
    ttl?: number
): Promise<T> {
    const cacheKey = `${url}:${JSON.stringify(options || {})}`;

    return apiCache.getOrFetch(
        cacheKey,
        async () => {
            console.log('[API Cache] Fetching:', url);
            console.log('[API Cache] Options:', options);
            try {
                // 验证 URL
                if (!url || typeof url !== 'string') {
                    throw new Error(`Invalid URL: ${url}`);
                }

                const response = await fetch(url, options);
                console.log('[API Cache] Response status:', response.status, 'for', url);

                // Handle 304 Not Modified - return cached data if available
                if (response.status === 304) {
                    const cachedData = apiCache.get<T>(cacheKey);
                    if (cachedData !== null) {
                        console.log('[API Cache] Using cached data for 304 response:', url);
                        return cachedData;
                    }
                    // If no cached data, treat as error
                    throw new Error('304 Not Modified but no cached data available');
                }

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
                }

                // Handle empty responses
                const text = await response.text();
                if (!text) {
                    console.warn('[API Cache] Empty response from:', url);
                    throw new Error('Empty response from server');
                }

                try {
                    return JSON.parse(text) as T;
                } catch (e) {
                    console.error('[API Cache] Failed to parse JSON from:', url, 'Response:', text.substring(0, 200));
                    throw new Error(`Failed to parse JSON response: ${e instanceof Error ? e.message : 'Unknown error'}`);
                }
            } catch (error) {
                console.error('[API Cache] Fetch error details:', {
                    url,
                    error: error instanceof Error ? error.message : String(error),
                    errorType: error?.constructor?.name,
                    stack: error instanceof Error ? error.stack : undefined
                });

                // If fetch fails completely, check if we have cached data
                if (error instanceof TypeError && error.message === 'Failed to fetch') {
                    const cachedData = apiCache.get<T>(cacheKey);
                    if (cachedData !== null) {
                        console.warn('[API Cache] Fetch failed, using stale cached data for:', url);
                        return cachedData;
                    }
                }
                // Re-throw the error if no cached data available
                throw error;
            }
        },
        ttl
    );
}

// Clear cache for specific URL pattern
export function clearCacheByPattern(pattern: string): void {
    const keysToDelete: string[] = [];

    for (const key of apiCache['cache'].keys()) {
        if (key.includes(pattern)) {
            keysToDelete.push(key);
        }
    }

    keysToDelete.forEach(key => apiCache.delete(key));
}
