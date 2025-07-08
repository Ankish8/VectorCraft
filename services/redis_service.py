"""
Redis service for caching and session management
"""

import os
import json
import pickle
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching and session management"""
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client = None
        self.connected = False
        
        # Cache configuration
        self.default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', 3600))  # 1 hour
        self.long_ttl = int(os.getenv('CACHE_LONG_TTL', 86400))  # 24 hours
        self.short_ttl = int(os.getenv('CACHE_SHORT_TTL', 300))  # 5 minutes
        
        # Key prefixes
        self.prefixes = {
            'api_cache': 'api_cache:',
            'user_session': 'user_session:',
            'vectorization_cache': 'vectorization_cache:',
            'rate_limit': 'rate_limit:',
            'task_result': 'task_result:',
            'health_check': 'health_check:',
            'analytics': 'analytics:'
        }
        
        self.connect()
    
    def connect(self):
        """Connect to Redis server"""
        try:
            # Parse Redis URL
            if self.redis_url.startswith('redis://'):
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            else:
                # Default connection
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=int(os.getenv('REDIS_DB', 0)),
                    password=os.getenv('REDIS_PASSWORD'),
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            
            # Test connection
            self.redis_client.ping()
            self.connected = True
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.connected or not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except:
            self.connected = False
            return False
    
    def reconnect(self):
        """Reconnect to Redis"""
        logger.info("Attempting to reconnect to Redis...")
        self.connect()
    
    def _get_key(self, prefix: str, key: str) -> str:
        """Get full key with prefix"""
        return f"{self.prefixes.get(prefix, '')}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        if value is None:
            return None
        
        try:
            # Try JSON first
            return json.loads(value.decode('utf-8'))
        except:
            try:
                # Fall back to pickle
                return pickle.loads(value)
            except:
                # Return as string if all else fails
                return value.decode('utf-8')
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, prefix: str = 'api_cache') -> bool:
        """Set a key-value pair in Redis"""
        if not self.is_connected():
            logger.warning("Redis not connected, cannot set value")
            return False
        
        try:
            full_key = self._get_key(prefix, key)
            serialized_value = self._serialize_value(value)
            
            if ttl is None:
                ttl = self.default_ttl
            
            result = self.redis_client.setex(full_key, ttl, serialized_value)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to set Redis key {key}: {e}")
            return False
    
    def get(self, key: str, prefix: str = 'api_cache') -> Any:
        """Get a value from Redis"""
        if not self.is_connected():
            logger.warning("Redis not connected, cannot get value")
            return None
        
        try:
            full_key = self._get_key(prefix, key)
            value = self.redis_client.get(full_key)
            
            if value is None:
                return None
            
            return self._deserialize_value(value)
            
        except Exception as e:
            logger.error(f"Failed to get Redis key {key}: {e}")
            return None
    
    def delete(self, key: str, prefix: str = 'api_cache') -> bool:
        """Delete a key from Redis"""
        if not self.is_connected():
            logger.warning("Redis not connected, cannot delete value")
            return False
        
        try:
            full_key = self._get_key(prefix, key)
            result = self.redis_client.delete(full_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to delete Redis key {key}: {e}")
            return False
    
    def exists(self, key: str, prefix: str = 'api_cache') -> bool:
        """Check if a key exists in Redis"""
        if not self.is_connected():
            return False
        
        try:
            full_key = self._get_key(prefix, key)
            return bool(self.redis_client.exists(full_key))
            
        except Exception as e:
            logger.error(f"Failed to check Redis key {key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int, prefix: str = 'api_cache') -> bool:
        """Set expiration for a key"""
        if not self.is_connected():
            return False
        
        try:
            full_key = self._get_key(prefix, key)
            result = self.redis_client.expire(full_key, ttl)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to set expiration for Redis key {key}: {e}")
            return False
    
    def ttl(self, key: str, prefix: str = 'api_cache') -> int:
        """Get time to live for a key"""
        if not self.is_connected():
            return -1
        
        try:
            full_key = self._get_key(prefix, key)
            return self.redis_client.ttl(full_key)
            
        except Exception as e:
            logger.error(f"Failed to get TTL for Redis key {key}: {e}")
            return -1
    
    def keys(self, pattern: str, prefix: str = 'api_cache') -> List[str]:
        """Get keys matching a pattern"""
        if not self.is_connected():
            return []
        
        try:
            full_pattern = self._get_key(prefix, pattern)
            keys = self.redis_client.keys(full_pattern)
            
            # Remove prefix from keys
            prefix_len = len(self.prefixes.get(prefix, ''))
            return [key.decode('utf-8')[prefix_len:] for key in keys]
            
        except Exception as e:
            logger.error(f"Failed to get Redis keys for pattern {pattern}: {e}")
            return []
    
    def flush_prefix(self, prefix: str) -> bool:
        """Flush all keys with a specific prefix"""
        if not self.is_connected():
            return False
        
        try:
            pattern = f"{self.prefixes.get(prefix, '')}*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                result = self.redis_client.delete(*keys)
                return bool(result)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to flush Redis prefix {prefix}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1, prefix: str = 'api_cache') -> Optional[int]:
        """Increment a numeric value"""
        if not self.is_connected():
            return None
        
        try:
            full_key = self._get_key(prefix, key)
            result = self.redis_client.incrby(full_key, amount)
            return result
            
        except Exception as e:
            logger.error(f"Failed to increment Redis key {key}: {e}")
            return None
    
    def decrement(self, key: str, amount: int = 1, prefix: str = 'api_cache') -> Optional[int]:
        """Decrement a numeric value"""
        if not self.is_connected():
            return None
        
        try:
            full_key = self._get_key(prefix, key)
            result = self.redis_client.decrby(full_key, amount)
            return result
            
        except Exception as e:
            logger.error(f"Failed to decrement Redis key {key}: {e}")
            return None
    
    def hash_set(self, key: str, field: str, value: Any, prefix: str = 'api_cache') -> bool:
        """Set a field in a hash"""
        if not self.is_connected():
            return False
        
        try:
            full_key = self._get_key(prefix, key)
            serialized_value = self._serialize_value(value)
            result = self.redis_client.hset(full_key, field, serialized_value)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to set hash field {field} in key {key}: {e}")
            return False
    
    def hash_get(self, key: str, field: str, prefix: str = 'api_cache') -> Any:
        """Get a field from a hash"""
        if not self.is_connected():
            return None
        
        try:
            full_key = self._get_key(prefix, key)
            value = self.redis_client.hget(full_key, field)
            
            if value is None:
                return None
            
            return self._deserialize_value(value)
            
        except Exception as e:
            logger.error(f"Failed to get hash field {field} from key {key}: {e}")
            return None
    
    def hash_get_all(self, key: str, prefix: str = 'api_cache') -> Dict[str, Any]:
        """Get all fields from a hash"""
        if not self.is_connected():
            return {}
        
        try:
            full_key = self._get_key(prefix, key)
            hash_data = self.redis_client.hgetall(full_key)
            
            result = {}
            for field, value in hash_data.items():
                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                result[field_str] = self._deserialize_value(value)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get hash data from key {key}: {e}")
            return {}
    
    def list_push(self, key: str, value: Any, prefix: str = 'api_cache') -> bool:
        """Push a value to a list"""
        if not self.is_connected():
            return False
        
        try:
            full_key = self._get_key(prefix, key)
            serialized_value = self._serialize_value(value)
            result = self.redis_client.lpush(full_key, serialized_value)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to push to list key {key}: {e}")
            return False
    
    def list_pop(self, key: str, prefix: str = 'api_cache') -> Any:
        """Pop a value from a list"""
        if not self.is_connected():
            return None
        
        try:
            full_key = self._get_key(prefix, key)
            value = self.redis_client.rpop(full_key)
            
            if value is None:
                return None
            
            return self._deserialize_value(value)
            
        except Exception as e:
            logger.error(f"Failed to pop from list key {key}: {e}")
            return None
    
    def list_length(self, key: str, prefix: str = 'api_cache') -> int:
        """Get length of a list"""
        if not self.is_connected():
            return 0
        
        try:
            full_key = self._get_key(prefix, key)
            return self.redis_client.llen(full_key)
            
        except Exception as e:
            logger.error(f"Failed to get list length for key {key}: {e}")
            return 0
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        if not self.is_connected():
            return {}
        
        try:
            info = self.redis_client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0),
                'redis_version': info.get('redis_version', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            start_time = datetime.now()
            
            # Test basic operations
            test_key = 'health_check_test'
            test_value = {'timestamp': start_time.isoformat()}
            
            # Set test value
            set_success = self.set(test_key, test_value, ttl=60, prefix='health_check')
            
            # Get test value
            get_result = self.get(test_key, prefix='health_check')
            get_success = get_result is not None
            
            # Delete test value
            delete_success = self.delete(test_key, prefix='health_check')
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000  # ms
            
            return {
                'connected': self.is_connected(),
                'set_success': set_success,
                'get_success': get_success,
                'delete_success': delete_success,
                'response_time_ms': response_time,
                'status': 'healthy' if all([set_success, get_success, delete_success]) else 'unhealthy',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'connected': False,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Global Redis service instance
redis_service = RedisService()


# Decorator for caching function results
def cache_result(key_prefix: str = 'func_cache', ttl: Optional[int] = None, 
                prefix: str = 'api_cache'):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = redis_service.get(cache_key, prefix=prefix)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            redis_service.set(cache_key, result, ttl=ttl, prefix=prefix)
            
            return result
        return wrapper
    return decorator


if __name__ == '__main__':
    # Test Redis service
    logger.info("Testing Redis service...")
    
    # Test basic operations
    redis_service.set('test_key', 'test_value', ttl=60)
    value = redis_service.get('test_key')
    print(f"Test value: {value}")
    
    # Test health check
    health = redis_service.health_check()
    print(f"Health check: {health}")
    
    # Test info
    info = redis_service.get_info()
    print(f"Redis info: {info}")
    
    logger.info("Redis service test completed!")