"""
Advanced Cache Manager for Oakville Real Estate Analyzer
Implements multi-layer caching with in-memory, file-based, and Redis support
"""

import json
import hashlib
import time
import pickle
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Tuple
from functools import wraps
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
from dataclasses import dataclass, asdict
import redis

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    hits: int = 0
    source: str = "unknown"
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl <= 0:  # No expiration
            return False
        return time.time() - self.timestamp > self.ttl
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)


class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            self.stats['total_requests'] += 1
            
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.stats['misses'] += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.hits += 1
            self.stats['hits'] += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 3600, source: str = "unknown"):
        """Set value in cache"""
        with self.lock:
            # Remove if exists to update position
            if key in self.cache:
                del self.cache[key]
            
            # Add new entry
            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                source=source
            )
            
            # Evict oldest if over capacity
            while len(self.cache) > self.max_size:
                evicted_key = next(iter(self.cache))
                del self.cache[evicted_key]
                self.stats['evictions'] += 1
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            hit_rate = (self.stats['hits'] / self.stats['total_requests'] * 100 
                       if self.stats['total_requests'] > 0 else 0)
            return {
                **self.stats,
                'hit_rate': f"{hit_rate:.2f}%",
                'size': len(self.cache),
                'max_size': self.max_size
            }


class FileCache:
    """Persistent file-based cache"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent.parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / 'cache_index.json'
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load cache index from file"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache index: {e}")
        return {}
    
    def _save_index(self):
        """Save cache index to file"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key"""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache"""
        if key not in self.index:
            return None
        
        entry_info = self.index[key]
        
        # Check expiration
        if entry_info['ttl'] > 0:
            elapsed = time.time() - entry_info['timestamp']
            if elapsed > entry_info['ttl']:
                self.delete(key)
                return None
        
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            del self.index[key]
            self._save_index()
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load cache file for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 86400):
        """Set value in file cache"""
        cache_file = self._get_cache_file(key)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
            
            self.index[key] = {
                'timestamp': time.time(),
                'ttl': ttl,
                'file': str(cache_file.name)
            }
            self._save_index()
            
        except Exception as e:
            logger.error(f"Failed to save cache file for {key}: {e}")
    
    def delete(self, key: str):
        """Delete entry from file cache"""
        if key in self.index:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
            del self.index[key]
            self._save_index()
    
    def clear(self):
        """Clear all file cache"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        self.index.clear()
        self._save_index()


class RedisCache:
    """Redis-based distributed cache"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        self.enabled = False
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False
            )
            self.client.ping()
            self.enabled = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis not available, skipping: {e}")
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.enabled:
            return None
        
        try:
            data = self.client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in Redis"""
        if not self.enabled:
            return
        
        try:
            data = pickle.dumps(value)
            self.client.setex(key, ttl, data)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete key from Redis"""
        if not self.enabled:
            return
        
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear(self):
        """Clear all Redis cache"""
        if not self.enabled:
            return
        
        try:
            self.client.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")


class CacheManager:
    """
    Multi-layer cache manager with automatic fallback
    Layer 1: In-memory LRU cache (fastest, limited size)
    Layer 2: Redis cache (fast, distributed)
    Layer 3: File cache (persistent, slower)
    """
    
    def __init__(self, 
                 memory_size: int = 1000,
                 enable_redis: bool = True,
                 enable_file: bool = True,
                 cache_dir: Path = None):
        
        self.memory_cache = LRUCache(max_size=memory_size)
        self.redis_cache = RedisCache() if enable_redis else None
        self.file_cache = FileCache(cache_dir) if enable_file else None
        
        # Request deduplication
        self.pending_requests: Dict[str, threading.Event] = {}
        self.pending_lock = threading.Lock()
        
        # Cache configuration
        self.default_ttl = {
            'api_response': 3600,      # 1 hour
            'geocoding': 86400,        # 24 hours
            'zoning': 7200,            # 2 hours
            'valuation': 1800,         # 30 minutes
            'analysis': 900            # 15 minutes
        }
    
    def _generate_key(self, prefix: str, params: Any) -> str:
        """Generate cache key from prefix and parameters"""
        if isinstance(params, (dict, list)):
            params_str = json.dumps(params, sort_keys=True)
        else:
            params_str = str(params)
        
        hash_str = hashlib.md5(params_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_str}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with multi-layer fallback"""
        # Layer 1: Memory cache
        value = self.memory_cache.get(key)
        if value is not None:
            logger.debug(f"Cache hit (memory): {key}")
            return value
        
        # Layer 2: Redis cache
        if self.redis_cache:
            value = self.redis_cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit (redis): {key}")
                # Promote to memory cache
                self.memory_cache.set(key, value, ttl=300)
                return value
        
        # Layer 3: File cache
        if self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit (file): {key}")
                # Promote to faster caches
                self.memory_cache.set(key, value, ttl=300)
                if self.redis_cache:
                    self.redis_cache.set(key, value, ttl=3600)
                return value
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = None, cache_type: str = None):
        """Set value in all cache layers"""
        if ttl is None:
            ttl = self.default_ttl.get(cache_type, 3600)
        
        # Set in all layers
        self.memory_cache.set(key, value, ttl=ttl, source=cache_type or "unknown")
        
        if self.redis_cache:
            self.redis_cache.set(key, value, ttl=ttl)
        
        if self.file_cache:
            self.file_cache.set(key, value, ttl=ttl * 2)  # Longer TTL for file cache
        
        logger.debug(f"Cache set: {key} (ttl={ttl})")
    
    def delete(self, key: str):
        """Delete from all cache layers"""
        self.memory_cache.cache.pop(key, None)
        
        if self.redis_cache:
            self.redis_cache.delete(key)
        
        if self.file_cache:
            self.file_cache.delete(key)
    
    def clear_pattern(self, pattern: str):
        """Clear cache entries matching pattern"""
        total_cleared = 0
        
        # Clear from memory cache
        keys_to_delete = [k for k in self.memory_cache.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.memory_cache.cache[key]
        total_cleared += len(keys_to_delete)
        
        # Clear from Redis cache (pattern matching)
        if self.redis_cache and self.redis_cache.enabled:
            try:
                redis_keys = self.redis_cache.client.keys(f"*{pattern}*")
                if redis_keys:
                    self.redis_cache.client.delete(*redis_keys)
                    total_cleared += len(redis_keys)
            except Exception as e:
                logger.error(f"Error clearing Redis pattern {pattern}: {e}")
        
        # Clear from file cache (pattern matching)
        if self.file_cache:
            file_keys_to_delete = [k for k in self.file_cache.index.keys() if pattern in k]
            for key in file_keys_to_delete:
                self.file_cache.delete(key)
            total_cleared += len(file_keys_to_delete)
        
        logger.info(f"Cleared {total_cleared} entries matching pattern: {pattern}")
        return total_cleared
    
    def deduplicate_request(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """
        Prevent duplicate concurrent requests for the same resource
        If a request is already in progress, wait for it to complete
        """
        with self.pending_lock:
            if key in self.pending_requests:
                # Request already in progress, wait for it
                event = self.pending_requests[key]
                logger.debug(f"Waiting for pending request: {key}")
                
                # Wait outside the lock with timeout
                self.pending_lock.release()
                try:
                    if event.wait(timeout=10):  # Reduced timeout to 10 seconds
                        # Request completed successfully, try to get from cache
                        result = self.get(key)
                        if result is not None:
                            return result
                        logger.warning(f"Request completed but no cached result for: {key}")
                    else:
                        logger.error(f"Request timed out waiting for: {key}")
                        # Clean up timed out request
                        with self.pending_lock:
                            if key in self.pending_requests:
                                del self.pending_requests[key]
                    
                    # If we get here, either timeout occurred or no cached result
                    # Fall back to executing the function ourselves
                    logger.info(f"Falling back to direct execution for: {key}")
                    return func(*args, **kwargs)
                    
                finally:
                    self.pending_lock.acquire()
                
            else:
                # New request, create event and execute
                event = threading.Event()
                self.pending_requests[key] = event
                
        # Execute the function (we have the lock or acquired it back)
        try:
            logger.debug(f"Executing new request: {key}")
            # Extract cache_type from kwargs before calling the original function
            cache_type = kwargs.pop('cache_type', 'api_response')
            result = func(*args, **kwargs)
            # Cache the result
            if result is not None:
                self.set(key, result, cache_type=cache_type)
            return result
        except Exception as e:
            logger.error(f"Error executing request {key}: {e}")
            raise
        finally:
            # Remove from pending and signal completion
            with self.pending_lock:
                if key in self.pending_requests:
                    del self.pending_requests[key]
            event.set()
    
    def clear_all_caches(self) -> Dict[str, int]:
        """Clear ALL cache data from all layers"""
        cleared_counts = {
            'memory': 0,
            'redis': 0,
            'file': 0
        }
        
        # Clear memory cache
        with self.memory_cache.lock:
            cleared_counts['memory'] = len(self.memory_cache.cache)
            self.memory_cache.cache.clear()
            # Reset stats
            self.memory_cache.stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'total_requests': 0
            }
        
        # Clear Redis cache
        if self.redis_cache and self.redis_cache.enabled:
            try:
                redis_info = self.redis_cache.client.info()
                cleared_counts['redis'] = redis_info.get('db0', {}).get('keys', 0)
                self.redis_cache.client.flushdb()
            except Exception as e:
                logger.error(f"Error clearing Redis cache: {e}")
        
        # Clear file cache
        if self.file_cache:
            cleared_counts['file'] = len(self.file_cache.index)
            self.file_cache.clear()
        
        total_cleared = sum(cleared_counts.values())
        logger.info(f"Cleared ALL caches - Total: {total_cleared} entries (Memory: {cleared_counts['memory']}, Redis: {cleared_counts['redis']}, File: {cleared_counts['file']})")
        
        return cleared_counts
    
    def clear_cache_by_type(self, cache_type: str) -> int:
        """Clear cache entries by type (api_response, zoning, etc.)"""
        return self.clear_pattern(cache_type)
    
    def clear_expired_entries(self) -> Dict[str, int]:
        """Clear only expired cache entries from all layers"""
        cleared_counts = {
            'memory': 0,
            'redis': 0,
            'file': 0
        }
        
        # Clear expired from memory cache
        with self.memory_cache.lock:
            expired_keys = [k for k, v in self.memory_cache.cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.memory_cache.cache[key]
            cleared_counts['memory'] = len(expired_keys)
        
        # Redis handles expiration automatically, but we can check
        if self.redis_cache and self.redis_cache.enabled:
            try:
                # Redis automatically removes expired keys, so we just report 0
                cleared_counts['redis'] = 0
            except Exception as e:
                logger.error(f"Error checking Redis expired entries: {e}")
        
        # Clear expired from file cache
        if self.file_cache:
            expired_file_keys = []
            current_time = time.time()
            for key, entry_info in self.file_cache.index.items():
                if entry_info['ttl'] > 0 and (current_time - entry_info['timestamp']) > entry_info['ttl']:
                    expired_file_keys.append(key)
            
            for key in expired_file_keys:
                self.file_cache.delete(key)
            cleared_counts['file'] = len(expired_file_keys)
        
        total_cleared = sum(cleared_counts.values())
        logger.info(f"Cleared expired entries - Total: {total_cleared} (Memory: {cleared_counts['memory']}, File: {cleared_counts['file']})")
        
        return cleared_counts
    
    def get_cache_size_info(self) -> Dict[str, Any]:
        """Get detailed cache size information"""
        info = {
            'memory': {
                'entries': len(self.memory_cache.cache),
                'max_size': self.memory_cache.max_size,
                'utilization_pct': (len(self.memory_cache.cache) / self.memory_cache.max_size * 100) if self.memory_cache.max_size > 0 else 0
            },
            'redis': {
                'enabled': self.redis_cache.enabled if self.redis_cache else False,
                'entries': 0
            },
            'file': {
                'enabled': self.file_cache is not None,
                'entries': len(self.file_cache.index) if self.file_cache else 0
            }
        }
        
        # Get Redis info if available
        if self.redis_cache and self.redis_cache.enabled:
            try:
                redis_info = self.redis_cache.client.info()
                info['redis']['entries'] = redis_info.get('db0', {}).get('keys', 0)
                info['redis']['memory_usage'] = redis_info.get('used_memory_human', 'Unknown')
            except Exception as e:
                logger.error(f"Error getting Redis info: {e}")
        
        # Calculate file cache size
        if self.file_cache:
            try:
                total_size = sum(f.stat().st_size for f in self.file_cache.cache_dir.glob('*.cache') if f.exists())
                info['file']['total_size_mb'] = total_size / (1024 * 1024)
                info['file']['cache_files'] = len(list(self.file_cache.cache_dir.glob('*.cache')))
            except Exception as e:
                logger.error(f"Error calculating file cache size: {e}")
                info['file']['total_size_mb'] = 0
                info['file']['cache_files'] = 0
        
        return info
    
    def get_stats(self) -> Dict:
        """Get comprehensive cache statistics"""
        stats = {
            'memory': self.memory_cache.get_stats(),
            'redis': {'enabled': self.redis_cache.enabled if self.redis_cache else False},
            'file': {'enabled': self.file_cache is not None},
            'pending_requests': len(self.pending_requests)
        }
        
        # Add size information
        size_info = self.get_cache_size_info()
        stats['size_info'] = size_info
        
        # Calculate total stats
        total_hits = stats['memory']['hits']
        total_requests = stats['memory']['total_requests']
        
        if total_requests > 0:
            overall_hit_rate = (total_hits / total_requests) * 100
            stats['overall_hit_rate'] = f"{overall_hit_rate:.2f}%"
        
        # Add total entries across all caches
        stats['total_entries'] = (
            size_info['memory']['entries'] + 
            size_info['redis']['entries'] + 
            size_info['file']['entries']
        )
        
        return stats


# Decorator for automatic caching
def cached(cache_type: str = 'api_response', ttl: int = None, key_prefix: str = None):
    """
    Decorator for automatic function result caching
    
    Usage:
        @cached(cache_type='zoning', ttl=7200)
        def get_zoning_info(lat, lon):
            # expensive API call
            return api_result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get or create cache manager
            if not hasattr(wrapper, '_cache_manager'):
                wrapper._cache_manager = CacheManager()
            
            # Generate cache key, excluding 'self' for instance methods
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            # Skip first argument if it looks like 'self' (instance method)
            cache_args = args[1:] if args and hasattr(args[0], '__class__') else args
            cache_key = wrapper._cache_manager._generate_key(
                prefix, 
                {'args': cache_args, 'kwargs': kwargs}
            )
            
            # Check cache first
            cached_result = wrapper._cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Use deduplication for concurrent requests
            # Prepare kwargs with cache_type for the cache manager
            cache_kwargs = kwargs.copy()
            cache_kwargs['cache_type'] = cache_type
            return wrapper._cache_manager.deduplicate_request(
                cache_key,
                func,
                *args,
                **cache_kwargs
            )
        
        wrapper.clear_cache = lambda: wrapper._cache_manager.clear_pattern(
            key_prefix or f"{func.__module__}.{func.__name__}"
        )
        wrapper.get_stats = lambda: wrapper._cache_manager.get_stats()
        wrapper.clear_all = lambda: wrapper._cache_manager.clear_all_caches()
        
        return wrapper
    return decorator


# Global cache manager instance
_global_cache_manager = None

def get_global_cache_manager() -> CacheManager:
    """Get or create global cache manager"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


# Convenience functions for cache management
def clear_all_caches() -> Dict[str, int]:
    """Clear all cache data from the global cache manager"""
    cache_manager = get_global_cache_manager()
    return cache_manager.clear_all_caches()


def clear_cache_by_type(cache_type: str) -> int:
    """Clear cache entries by type from the global cache manager"""
    cache_manager = get_global_cache_manager()
    return cache_manager.clear_cache_by_type(cache_type)


def clear_expired_cache_entries() -> Dict[str, int]:
    """Clear expired cache entries from the global cache manager"""
    cache_manager = get_global_cache_manager()
    return cache_manager.clear_expired_entries()


def get_cache_stats() -> Dict:
    """Get cache statistics from the global cache manager"""
    cache_manager = get_global_cache_manager()
    return cache_manager.get_stats()


def get_cache_size_info() -> Dict[str, Any]:
    """Get cache size information from the global cache manager"""
    cache_manager = get_global_cache_manager()
    return cache_manager.get_cache_size_info()


# Example usage and testing
if __name__ == "__main__":
    # Test the cache manager
    cache = CacheManager()
    
    # Test basic operations
    cache.set("test_key", {"data": "test_value"}, cache_type="api_response")
    print(f"Retrieved: {cache.get('test_key')}")
    
    # Test cache clearing functions
    print("\n=== Cache Management Testing ===")
    
    # Add some test data
    cache.set("api_test_1", {"data": "api_data_1"}, cache_type="api_response")
    cache.set("api_test_2", {"data": "api_data_2"}, cache_type="api_response")
    cache.set("zoning_test_1", {"zone": "RL3"}, cache_type="zoning")
    
    print(f"Initial cache stats: {json.dumps(cache.get_stats(), indent=2)}")
    
    # Test pattern clearing
    cleared = cache.clear_pattern("api_")
    print(f"Cleared {cleared} entries matching 'api_' pattern")
    
    # Test type clearing
    cleared = cache.clear_cache_by_type("zoning")
    print(f"Cleared {cleared} zoning cache entries")
    
    # Test size info
    size_info = cache.get_cache_size_info()
    print(f"Cache size info: {json.dumps(size_info, indent=2)}")
    
    # Test global functions
    print("\n=== Global Functions Testing ===")
    global_stats = get_cache_stats()
    print(f"Global cache stats: {json.dumps(global_stats, indent=2)}")
    
    # Test decorator
    @cached(cache_type='zoning', ttl=60)
    def expensive_operation(x, y):
        print(f"Executing expensive operation({x}, {y})")
        time.sleep(1)
        return x + y
    
    # First call - executes function
    result1 = expensive_operation(5, 3)
    print(f"Result 1: {result1}")
    
    # Second call - returns from cache
    result2 = expensive_operation(5, 3)
    print(f"Result 2: {result2}")
    
    print(f"Function cache stats: {expensive_operation.get_stats()}")
    
    # Test full cache clearing
    print("\n=== Full Cache Clear Test ===")
    cleared_counts = clear_all_caches()
    print(f"Cleared all caches: {cleared_counts}")
    
    final_stats = get_cache_stats()
    print(f"Final cache stats: {json.dumps(final_stats, indent=2)}")