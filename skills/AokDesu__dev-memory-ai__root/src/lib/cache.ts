/**
 * Caching Layer for Embeddings and Search Results
 * Improves performance by caching frequently accessed data
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

export interface CacheEntry<T> {
  key: string;
  value: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
  hits: number;
}

export interface CacheStats {
  size: number;
  hits: number;
  misses: number;
  hitRate: number;
  evictions: number;
}

/**
 * In-memory LRU Cache with TTL support
 */
export class LRUCache<T> {
  private cache: Map<string, CacheEntry<T>> = new Map();
  private maxSize: number;
  private defaultTTL: number;
  private stats = {
    hits: 0,
    misses: 0,
    evictions: 0,
  };

  constructor(maxSize: number = 1000, defaultTTL: number = 3600000) {
    // Default: 1000 entries, 1 hour TTL
    this.maxSize = maxSize;
    this.defaultTTL = defaultTTL;
  }

  /**
   * Get value from cache
   */
  get(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      this.stats.misses++;
      return null;
    }

    // Check if expired
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      this.stats.misses++;
      return null;
    }

    // Update hits and move to end (most recently used)
    entry.hits++;
    this.stats.hits++;
    this.cache.delete(key);
    this.cache.set(key, entry);

    return entry.value;
  }

  /**
   * Set value in cache
   */
  set(key: string, value: T, ttl?: number): void {
    // Evict if at capacity
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      this.evictLRU();
    }

    const entry: CacheEntry<T> = {
      key,
      value,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL,
      hits: 0,
    };

    this.cache.set(key, entry);
  }

  /**
   * Check if key exists in cache
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;

    // Check if expired
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return false;
    }

    return true;
  }

  /**
   * Delete key from cache
   */
  delete(key: string): boolean {
    return this.cache.delete(key);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.stats = {
      hits: 0,
      misses: 0,
      evictions: 0,
    };
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    const total = this.stats.hits + this.stats.misses;
    const hitRate = total > 0 ? this.stats.hits / total : 0;

    return {
      size: this.cache.size,
      hits: this.stats.hits,
      misses: this.stats.misses,
      hitRate,
      evictions: this.stats.evictions,
    };
  }

  /**
   * Evict least recently used entry
   */
  private evictLRU(): void {
    const firstKey = this.cache.keys().next().value;
    if (firstKey) {
      this.cache.delete(firstKey);
      this.stats.evictions++;
    }
  }

  /**
   * Clean up expired entries
   */
  cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * Get all keys
   */
  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  /**
   * Get cache size
   */
  size(): number {
    return this.cache.size;
  }
}

/**
 * Persistent cache using file system
 */
export class PersistentCache<T> {
  private cacheDir: string;
  private memoryCache: LRUCache<T>;

  constructor(cacheDir: string = '.cache', maxMemorySize: number = 500) {
    this.cacheDir = path.join(process.cwd(), cacheDir);
    this.memoryCache = new LRUCache<T>(maxMemorySize);

    // Create cache directory if it doesn't exist
    if (!fs.existsSync(this.cacheDir)) {
      fs.mkdirSync(this.cacheDir, { recursive: true });
    }
  }

  /**
   * Generate cache key hash
   */
  private hashKey(key: string): string {
    return crypto.createHash('md5').update(key).digest('hex');
  }

  /**
   * Get cache file path
   */
  private getCacheFilePath(key: string): string {
    const hash = this.hashKey(key);
    return path.join(this.cacheDir, `${hash}.json`);
  }

  /**
   * Get value from cache (memory first, then disk)
   */
  async get(key: string): Promise<T | null> {
    // Try memory cache first
    const memoryValue = this.memoryCache.get(key);
    if (memoryValue !== null) {
      return memoryValue;
    }

    // Try disk cache
    try {
      const filePath = this.getCacheFilePath(key);
      if (fs.existsSync(filePath)) {
        const data = fs.readFileSync(filePath, 'utf-8');
        const entry: CacheEntry<T> = JSON.parse(data);

        // Check if expired
        if (Date.now() - entry.timestamp > entry.ttl) {
          fs.unlinkSync(filePath);
          return null;
        }

        // Load into memory cache
        this.memoryCache.set(key, entry.value, entry.ttl);
        return entry.value;
      }
    } catch (error) {
      console.error(`Error reading cache for key ${key}:`, error);
    }

    return null;
  }

  /**
   * Set value in cache (both memory and disk)
   */
  async set(key: string, value: T, ttl?: number): Promise<void> {
    const actualTTL = ttl || 3600000; // 1 hour default

    // Set in memory cache
    this.memoryCache.set(key, value, actualTTL);

    // Write to disk
    try {
      const entry: CacheEntry<T> = {
        key,
        value,
        timestamp: Date.now(),
        ttl: actualTTL,
        hits: 0,
      };

      const filePath = this.getCacheFilePath(key);
      fs.writeFileSync(filePath, JSON.stringify(entry), 'utf-8');
    } catch (error) {
      console.error(`Error writing cache for key ${key}:`, error);
    }
  }

  /**
   * Delete key from cache
   */
  async delete(key: string): Promise<void> {
    this.memoryCache.delete(key);

    try {
      const filePath = this.getCacheFilePath(key);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch (error) {
      console.error(`Error deleting cache for key ${key}:`, error);
    }
  }

  /**
   * Clear all cache
   */
  async clear(): Promise<void> {
    this.memoryCache.clear();

    try {
      const files = fs.readdirSync(this.cacheDir);
      for (const file of files) {
        fs.unlinkSync(path.join(this.cacheDir, file));
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  }

  /**
   * Clean up expired entries
   */
  async cleanup(): Promise<void> {
    this.memoryCache.cleanup();

    try {
      const files = fs.readdirSync(this.cacheDir);
      const now = Date.now();

      for (const file of files) {
        const filePath = path.join(this.cacheDir, file);
        try {
          const data = fs.readFileSync(filePath, 'utf-8');
          const entry: CacheEntry<T> = JSON.parse(data);

          if (now - entry.timestamp > entry.ttl) {
            fs.unlinkSync(filePath);
          }
        } catch (error) {
          // Invalid cache file, delete it
          fs.unlinkSync(filePath);
        }
      }
    } catch (error) {
      console.error('Error cleaning up cache:', error);
    }
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return this.memoryCache.getStats();
  }
}

/**
 * Embedding Cache - specialized cache for embeddings
 */
export class EmbeddingCache {
  private cache: PersistentCache<number[]>;

  constructor(cacheDir: string = '.cache/embeddings') {
    this.cache = new PersistentCache<number[]>(cacheDir, 1000);
  }

  /**
   * Generate cache key for text
   */
  private generateKey(text: string, model: string): string {
    const hash = crypto.createHash('sha256').update(text).digest('hex');
    return `${model}:${hash}`;
  }

  /**
   * Get embedding from cache
   */
  async get(text: string, model: string): Promise<number[] | null> {
    const key = this.generateKey(text, model);
    return await this.cache.get(key);
  }

  /**
   * Set embedding in cache
   */
  async set(text: string, model: string, embedding: number[]): Promise<void> {
    const key = this.generateKey(text, model);
    // Cache embeddings for 7 days
    await this.cache.set(key, embedding, 7 * 24 * 60 * 60 * 1000);
  }

  /**
   * Batch get embeddings
   */
  async batchGet(
    texts: string[],
    model: string
  ): Promise<Map<string, number[] | null>> {
    const results = new Map<string, number[] | null>();

    for (const text of texts) {
      const embedding = await this.get(text, model);
      results.set(text, embedding);
    }

    return results;
  }

  /**
   * Batch set embeddings
   */
  async batchSet(
    items: Array<{ text: string; embedding: number[] }>,
    model: string
  ): Promise<void> {
    for (const item of items) {
      await this.set(item.text, model, item.embedding);
    }
  }

  /**
   * Clear embedding cache
   */
  async clear(): Promise<void> {
    await this.cache.clear();
  }

  /**
   * Remove only expired embeddings (preserves still-valid 7-day TTL entries).
   */
  async cleanup(): Promise<void> {
    await this.cache.cleanup();
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return this.cache.getStats();
  }
}

/**
 * Search Results Cache
 */
export class SearchCache {
  private cache: LRUCache<any>;

  constructor(maxSize: number = 500) {
    this.cache = new LRUCache<any>(maxSize, 600000); // 10 minutes TTL
  }

  /**
   * Generate cache key for search query
   */
  private generateKey(query: string, filters?: any): string {
    const filterStr = filters ? JSON.stringify(filters) : '';
    return crypto
      .createHash('sha256')
      .update(`${query}:${filterStr}`)
      .digest('hex');
  }

  /**
   * Get search results from cache
   */
  get(query: string, filters?: any): any | null {
    const key = this.generateKey(query, filters);
    return this.cache.get(key);
  }

  /**
   * Set search results in cache
   */
  set(query: string, results: any, filters?: any): void {
    const key = this.generateKey(query, filters);
    this.cache.set(key, results);
  }

  /**
   * Clear search cache
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Remove only expired search entries.
   */
  cleanup(): void {
    this.cache.cleanup();
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return this.cache.getStats();
  }
}

// Singleton instances
let embeddingCache: EmbeddingCache | null = null;
let searchCache: SearchCache | null = null;

/**
 * Get embedding cache instance
 */
export function getEmbeddingCache(): EmbeddingCache {
  if (!embeddingCache) {
    embeddingCache = new EmbeddingCache();
  }
  return embeddingCache;
}

/**
 * Get search cache instance
 */
export function getSearchCache(): SearchCache {
  if (!searchCache) {
    searchCache = new SearchCache();
  }
  return searchCache;
}

/**
 * Schedule periodic cache cleanup
 */
export function scheduleCacheCleanup(intervalMs: number = 3600000): NodeJS.Timeout {
  return setInterval(async () => {
    try {
      await getEmbeddingCache().cleanup();
      getSearchCache().cleanup();
      console.log('Cache cleanup completed');
    } catch (error) {
      console.error('Cache cleanup failed:', error);
    }
  }, intervalMs);
}

// Made with Bob
