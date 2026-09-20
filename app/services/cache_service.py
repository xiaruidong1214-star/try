import hashlib
import json
import logging
import redis
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 缓存服务"""
    
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.default_ttl = 3600  # 1小时
    
    @staticmethod
    def make_cache_key(code: str, language: str) -> str:
        """根据代码内容生成缓存 key（SHA256）"""
        content = f"{language}:{code.strip()}"
        hash_val = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"review:cache:{hash_val}"
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """读取缓存"""
        try:
            data = self.client.get(cache_key)
            if data:
                logger.info(f"Cache HIT: {cache_key}")
                return json.loads(data)
            logger.info(f"Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, cache_key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        """写入缓存"""
        try:
            ttl = ttl or self.default_ttl
            self.client.setex(cache_key, ttl, json.dumps(value, ensure_ascii=False))
            logger.info(f"Cache SET: {cache_key} (ttl={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def acquire_lock(self, lock_key: str, timeout: int = 30) -> bool:
        """获取分布式锁（防缓存击穿）"""
        try:
            return bool(self.client.set(lock_key, "1", nx=True, ex=timeout))
        except Exception as e:
            logger.error(f"Lock acquire error: {e}")
            return False
    
    def release_lock(self, lock_key: str) -> None:
        """释放分布式锁"""
        try:
            self.client.delete(lock_key)
        except Exception as e:
            logger.error(f"Lock release error: {e}")


# 全局单例
cache_service = CacheService()