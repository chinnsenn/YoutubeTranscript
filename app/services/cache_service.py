import redis.asyncio as redis
import json
import os
from typing import Optional
from datetime import datetime, timedelta
from app.models import TranscriptResponse
import logging


class CacheService:
    def __init__(self):
        self.redis = None
        self.logger = logging.getLogger(__name__)
        self.default_ttl = int(os.getenv('CACHE_TTL', 3600))  # 1 hour default
        
    async def connect(self):
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis = redis.from_url(redis_url, decode_responses=True)
            await self.redis.ping()
            self.logger.info("Connected to Redis cache")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def disconnect(self):
        if self.redis:
            await self.redis.close()
    
    def _get_cache_key(self, video_id: str, language: str = "en") -> str:
        return f"transcript:{video_id}:{language}"
    
    async def get_transcript(self, video_id: str, language: str = "en") -> Optional[TranscriptResponse]:
        if not self.redis:
            return None
            
        try:
            cache_key = self._get_cache_key(video_id, language)
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                # Parse the timestamp
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                data['cached'] = True
                return TranscriptResponse(**data)
                
        except Exception as e:
            self.logger.error(f"Error retrieving from cache: {e}")
            
        return None
    
    async def set_transcript(self, video_id: str, language: str, transcript: TranscriptResponse, ttl: Optional[int] = None):
        if not self.redis:
            return
            
        try:
            cache_key = self._get_cache_key(video_id, language)
            
            # Convert to dict for JSON serialization
            data = transcript.dict()
            data['timestamp'] = transcript.timestamp.isoformat()
            
            # Convert segments to dict format
            data['segments'] = [segment.dict() for segment in transcript.segments]
            
            cache_ttl = ttl or self.default_ttl
            await self.redis.setex(cache_key, cache_ttl, json.dumps(data))
            
            self.logger.info(f"Cached transcript for {video_id}:{language}")
            
        except Exception as e:
            self.logger.error(f"Error setting cache: {e}")
    
    async def delete_transcript(self, video_id: str, language: str = "en"):
        if not self.redis:
            return
            
        try:
            cache_key = self._get_cache_key(video_id, language)
            await self.redis.delete(cache_key)
            self.logger.info(f"Deleted cache for {video_id}:{language}")
            
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {e}")
    
    async def clear_all_cache(self):
        if not self.redis:
            return
            
        try:
            pattern = "transcript:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                self.logger.info(f"Cleared {len(keys)} cached transcripts")
                
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    async def get_cache_stats(self) -> dict:
        if not self.redis:
            return {"status": "disabled"}
            
        try:
            info = await self.redis.info()
            pattern = "transcript:*"
            keys = await self.redis.keys(pattern)
            
            return {
                "status": "connected",
                "cached_transcripts": len(keys),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "message": str(e)}


cache_service = CacheService()