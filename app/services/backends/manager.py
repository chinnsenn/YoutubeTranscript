import os
from typing import List, Dict, Any, Optional
from enum import Enum
from app.models import TranscriptSegment
from .base import TranscriptBackend, BackendInfo
from .youtube_transcript_api import YouTubeTranscriptApiBackend
from .yt_dlp import YtDlpBackend
import logging


class BackendType(Enum):
    YOUTUBE_TRANSCRIPT_API = "youtube_transcript_api"
    YT_DLP = "yt_dlp"


class BackendManager:
    """Manages multiple transcript backends with fallback logic"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._backends = {
            BackendType.YOUTUBE_TRANSCRIPT_API: YouTubeTranscriptApiBackend(),
            BackendType.YT_DLP: YtDlpBackend()
        }
        
        # Configure backend order from environment or use defaults
        self.primary_backend = self._get_backend_from_env("TRANSCRIPT_BACKEND_PRIMARY", BackendType.YOUTUBE_TRANSCRIPT_API)
        self.fallback_backend = self._get_backend_from_env("TRANSCRIPT_BACKEND_FALLBACK", BackendType.YT_DLP)
        
        self.logger.info(f"Primary backend: {self.primary_backend.value}")
        self.logger.info(f"Fallback backend: {self.fallback_backend.value}")
    
    def _get_backend_from_env(self, env_var: str, default: BackendType) -> BackendType:
        """Get backend type from environment variable"""
        backend_name = os.getenv(env_var, default.value)
        try:
            return BackendType(backend_name)
        except ValueError:
            self.logger.warning(f"Invalid backend name in {env_var}: {backend_name}, using default: {default.value}")
            return default
    
    async def get_transcript(
        self, 
        video_id: str, 
        language: str = "en",
        preferred_backend: Optional[BackendType] = None
    ) -> Dict[str, Any]:
        """
        Get transcript with automatic fallback between backends
        
        Args:
            video_id: YouTube video ID
            language: Language code for transcript
            preferred_backend: Optional backend preference for this request
            
        Returns:
            Dict containing transcript data and backend metadata
        """
        
        # Determine backend order
        if preferred_backend:
            backends_to_try = [preferred_backend]
            # Add other backends as fallbacks if different from preferred
            if preferred_backend != self.primary_backend:
                backends_to_try.append(self.primary_backend)
            if preferred_backend != self.fallback_backend and self.fallback_backend not in backends_to_try:
                backends_to_try.append(self.fallback_backend)
        else:
            backends_to_try = [self.primary_backend, self.fallback_backend]
        
        last_error = None
        
        for backend_type in backends_to_try:
            backend = self._backends[backend_type]
            
            if not backend.is_available():
                self.logger.warning(f"Backend {backend_type.value} is not available, skipping")
                continue
            
            try:
                self.logger.info(f"Trying backend: {backend_type.value}")
                
                result = await backend.get_transcript(video_id, language)
                
                # Add backend metadata to result
                result["backend_used"] = backend_type.value
                result["backend_info"] = backend.backend_info.__dict__
                
                self.logger.info(f"Successfully extracted transcript using {backend_type.value}")
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Backend {backend_type.value} failed: {str(e)}")
                continue
        
        # All backends failed
        error_msg = f"All backends failed to extract transcript for {video_id}"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        self.logger.error(error_msg)
        raise Exception(error_msg)
    
    async def get_available_languages(
        self, 
        video_id: str,
        preferred_backend: Optional[BackendType] = None
    ) -> List[str]:
        """Get available languages with backend fallback"""
        
        backends_to_try = [preferred_backend] if preferred_backend else [self.primary_backend, self.fallback_backend]
        
        for backend_type in backends_to_try:
            backend = self._backends[backend_type]
            
            if not backend.is_available():
                continue
            
            try:
                languages = await backend.get_available_languages(video_id)
                if languages:  # Return first successful result
                    return languages
            except Exception as e:
                self.logger.warning(f"Backend {backend_type.value} failed to get languages: {str(e)}")
                continue
        
        return []
    
    def get_backend_status(self) -> Dict[str, Any]:
        """Get status of all backends"""
        status = {}
        
        for backend_type, backend in self._backends.items():
            status[backend_type.value] = {
                "available": backend.is_available(),
                "info": backend.backend_info.__dict__
            }
        
        return {
            "backends": status,
            "primary": self.primary_backend.value,
            "fallback": self.fallback_backend.value
        }
    
    def get_backend(self, backend_type: BackendType) -> TranscriptBackend:
        """Get specific backend instance"""
        return self._backends[backend_type]


# Global backend manager instance
backend_manager = BackendManager()