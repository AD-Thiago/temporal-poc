"""
Redis cache layer for CUIDA+Care Worker
Provides caching for jobs, metrics, and aggregations with configurable TTL
"""
import json
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from .config import config
from .logging_config import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with connection pooling
    
    Returns:
        redis.Redis: Connected Redis client
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            logger.info(
                "Creating Redis client",
                host=config.redis.host,
                port=config.redis.port,
                db=config.redis.db
            )
            
            _redis_client = redis.Redis(
                host=config.redis.host,
                port=config.redis.port,
                password=config.redis.password if config.redis.password else None,
                db=config.redis.db,
                socket_timeout=config.redis.socket_timeout,
                socket_connect_timeout=config.redis.socket_timeout,
                decode_responses=True,  # Auto-decode bytes to strings
                health_check_interval=30,  # Health check every 30s
                retry_on_timeout=True,
                max_connections=10
            )
            
            # Test connection
            _redis_client.ping()
            logger.info("Redis client connected successfully")
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Failed to connect to Redis",
                error=str(e),
                host=config.redis.host,
                port=config.redis.port
            )
            raise
    
    return _redis_client


class CacheKey:
    """Cache key prefixes and builders"""
    
    JOB = "job"
    JOB_LIST = "job:list"
    METRICS = "metrics"
    AGGREGATION = "agg"
    
    @staticmethod
    def job(job_id: str) -> str:
        """Cache key for individual job"""
        return f"{CacheKey.JOB}:{job_id}"
    
    @staticmethod
    def job_list(status: str = None, page: int = 1, limit: int = 10) -> str:
        """Cache key for job list queries"""
        if status:
            return f"{CacheKey.JOB_LIST}:status:{status}:page:{page}:limit:{limit}"
        return f"{CacheKey.JOB_LIST}:page:{page}:limit:{limit}"
    
    @staticmethod
    def metrics(metric_name: str, window: str = "1h") -> str:
        """Cache key for metrics"""
        return f"{CacheKey.METRICS}:{metric_name}:{window}"
    
    @staticmethod
    def aggregation(agg_type: str, period: str = "hour") -> str:
        """Cache key for aggregations"""
        return f"{CacheKey.AGGREGATION}:{agg_type}:{period}"


def cache_get(key: str) -> Optional[Any]:
    """
    Get value from cache
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    try:
        client = get_redis_client()
        value = client.get(key)
        
        if value:
            logger.debug("Cache hit", key=key)
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        logger.debug("Cache miss", key=key)
        return None
        
    except RedisError as e:
        logger.error("Cache get failed", key=key, error=str(e))
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set value in cache with optional TTL
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (None = no expiration)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        
        # Serialize value to JSON
        if not isinstance(value, str):
            value = json.dumps(value, default=str)  # default=str handles datetime
        
        if ttl:
            client.setex(key, ttl, value)
        else:
            client.set(key, value)
        
        logger.debug("Cache set", key=key, ttl=ttl)
        return True
        
    except RedisError as e:
        logger.error("Cache set failed", key=key, error=str(e))
        return False


def cache_delete(key: str) -> bool:
    """
    Delete key from cache
    
    Args:
        key: Cache key
        
    Returns:
        True if key was deleted, False otherwise
    """
    try:
        client = get_redis_client()
        deleted = client.delete(key)
        logger.debug("Cache delete", key=key, deleted=bool(deleted))
        return bool(deleted)
        
    except RedisError as e:
        logger.error("Cache delete failed", key=key, error=str(e))
        return False


def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all keys matching pattern
    
    Args:
        pattern: Key pattern (e.g., "job:*")
        
    Returns:
        Number of keys deleted
    """
    try:
        client = get_redis_client()
        keys = client.keys(pattern)
        
        if keys:
            deleted = client.delete(*keys)
            logger.info("Cache invalidated", pattern=pattern, count=deleted)
            return deleted
        
        return 0
        
    except RedisError as e:
        logger.error("Cache invalidate failed", pattern=pattern, error=str(e))
        return 0


def cache_job(job_dict: Dict[str, Any]) -> bool:
    """
    Cache a job with appropriate TTL
    
    Args:
        job_dict: Job dictionary (from database model)
        
    Returns:
        True if cached successfully
    """
    job_id = job_dict.get('job_id')
    if not job_id:
        return False
    
    key = CacheKey.job(job_id)
    return cache_set(key, job_dict, ttl=config.redis.ttl_job)


def get_cached_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached job by ID
    
    Args:
        job_id: Job ID
        
    Returns:
        Job dictionary or None
    """
    key = CacheKey.job(job_id)
    return cache_get(key)


def invalidate_job(job_id: str) -> bool:
    """
    Invalidate cached job and related lists
    
    Args:
        job_id: Job ID
        
    Returns:
        True if invalidated
    """
    # Delete specific job
    job_key = CacheKey.job(job_id)
    cache_delete(job_key)
    
    # Invalidate all job lists (they might contain this job)
    cache_invalidate_pattern(f"{CacheKey.JOB_LIST}:*")
    
    return True


def cache_metrics(metric_name: str, value: Any, window: str = "1h") -> bool:
    """
    Cache metrics with short TTL
    
    Args:
        metric_name: Metric name
        value: Metric value
        window: Time window
        
    Returns:
        True if cached
    """
    key = CacheKey.metrics(metric_name, window)
    return cache_set(key, value, ttl=config.redis.ttl_metrics)


def get_cached_metrics(metric_name: str, window: str = "1h") -> Optional[Any]:
    """Get cached metrics"""
    key = CacheKey.metrics(metric_name, window)
    return cache_get(key)


def cache_aggregation(agg_type: str, value: Any, period: str = "hour") -> bool:
    """
    Cache aggregation results
    
    Args:
        agg_type: Aggregation type (e.g., "job_count", "avg_duration")
        value: Aggregated value
        period: Time period
        
    Returns:
        True if cached
    """
    key = CacheKey.aggregation(agg_type, period)
    return cache_set(key, value, ttl=config.redis.ttl_aggregations)


def get_cached_aggregation(agg_type: str, period: str = "hour") -> Optional[Any]:
    """Get cached aggregation"""
    key = CacheKey.aggregation(agg_type, period)
    return cache_get(key)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics
    
    Returns:
        Dictionary with cache stats
    """
    try:
        client = get_redis_client()
        info = client.info('stats')
        
        return {
            'connected': True,
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': (
                info.get('keyspace_hits', 0) / 
                (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1))
            ) * 100,
            'connected_clients': info.get('connected_clients', 0),
            'used_memory_human': client.info('memory').get('used_memory_human', 'unknown')
        }
        
    except RedisError as e:
        logger.error("Failed to get cache stats", error=str(e))
        return {'connected': False, 'error': str(e)}


def close_redis_connection():
    """Close Redis connection"""
    global _redis_client
    
    if _redis_client:
        logger.info("Closing Redis connection")
        _redis_client.close()
        _redis_client = None
