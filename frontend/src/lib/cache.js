/**
 * SearchCache class for client-side caching of search results
 * Implements a simple LRU (Least Recently Used) cache with expiration
 */
export class SearchCache {
    constructor(maxSize = 50, expirationTime = 5 * 60 * 1000) { // 5 minutes default
        this.cache = new Map();
        this.maxSize = maxSize;
        this.expirationTime = expirationTime;
    }

    /**
     * Generate a unique key for the search parameters
     */
    generateKey(searchTerm, page, perPage) {
        return `search:${searchTerm}:page:${page}:per:${perPage}`;
    }

    /**
     * Store search results in cache
     */
    set(searchTerm, page, perPage, data) {
        const key = this.generateKey(searchTerm, page, perPage);

        // If cache is at max size, remove oldest entry
        if (this.cache.size >= this.maxSize) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
        }

        this.cache.set(key, {
            data,
            timestamp: Date.now(),
            searchTerm,
            page,
            perPage
        });
    }

    /**
     * Retrieve search results from cache
     * Returns null if not found or expired
     */
    get(searchTerm, page, perPage) {
        const key = this.generateKey(searchTerm, page, perPage);
        const cached = this.cache.get(key);

        if (!cached) return null;

        // Check if cache has expired
        if (Date.now() - cached.timestamp > this.expirationTime) {
            this.cache.delete(key);
            return null;
        }

        return cached.data;
    }

    /**
     * Clear all cached data
     */
    clear() {
        this.cache.clear();
    }

    /**
     * Get all cached search terms
     */
    getCachedSearchTerms() {
        const terms = new Set();
        for (const [_, value] of this.cache) {
            terms.add(value.searchTerm);
        }
        return Array.from(terms);
    }

    /**
     * Remove all entries for a specific search term
     */
    invalidateSearchTerm(searchTerm) {
        for (const [key, value] of this.cache) {
            if (value.searchTerm === searchTerm) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Get cache statistics
     */
    getStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            uniqueSearchTerms: this.getCachedSearchTerms().length,
            oldestEntry: this.getOldestEntryAge(),
            newestEntry: this.getNewestEntryAge()
        };
    }

    /**
     * Get age of oldest cache entry in seconds
     */
    getOldestEntryAge() {
        let oldestTimestamp = Date.now();
        for (const [_, value] of this.cache) {
            if (value.timestamp < oldestTimestamp) {
                oldestTimestamp = value.timestamp;
            }
        }
        return Math.floor((Date.now() - oldestTimestamp) / 1000);
    }

    /**
     * Get age of newest cache entry in seconds
     */
    getNewestEntryAge() {
        let newestTimestamp = 0;
        for (const [_, value] of this.cache) {
            if (value.timestamp > newestTimestamp) {
                newestTimestamp = value.timestamp;
            }
        }
        return Math.floor((Date.now() - newestTimestamp) / 1000);
    }

    /**
     * Check if a search term exists in cache
     */
    has(searchTerm, page, perPage) {
        const key = this.generateKey(searchTerm, page, perPage);
        return this.cache.has(key);
    }

    /**
     * Remove expired entries from cache
     */
    cleanup() {
        const now = Date.now();
        for (const [key, value] of this.cache) {
            if (now - value.timestamp > this.expirationTime) {
                this.cache.delete(key);
            }
        }
    }
}

// Create and export a single instance
export const searchCache = new SearchCache();