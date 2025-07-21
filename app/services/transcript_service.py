import re
from typing import Optional, Dict, List
from datetime import datetime
from app.models import TranscriptResponse
from app.services.backends.manager import backend_manager, BackendType
import logging


class TranscriptService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backend_manager = backend_manager
        
    def extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL"""
        youtube_regex = re.compile(
            r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        )
        match = youtube_regex.search(url)
        if match:
            return match.group(1)
        raise ValueError("Invalid YouTube URL")
    
    async def get_transcript(
        self, 
        video_id: Optional[str] = None, 
        url: Optional[str] = None, 
        language: str = "en",
        backend: Optional[str] = None
    ) -> TranscriptResponse:
        """
        Get transcript using multi-backend approach with automatic fallback
        
        Args:
            video_id: YouTube video ID
            url: YouTube video URL (alternative to video_id)
            language: Language code for transcript
            backend: Optional backend preference ("youtube_transcript_api" or "yt_dlp")
        """
        if not video_id and not url:
            raise ValueError("Either video_id or url must be provided")
        
        if url and not video_id:
            video_id = self.extract_video_id(url)
        
        # Convert backend string to BackendType if provided
        preferred_backend = None
        if backend:
            try:
                preferred_backend = BackendType(backend)
            except ValueError:
                self.logger.warning(f"Invalid backend specified: {backend}, using default fallback")
        
        try:
            # Use backend manager to get transcript with fallback
            result = await self.backend_manager.get_transcript(
                video_id=video_id,
                language=language,
                preferred_backend=preferred_backend
            )
            
            # Convert to our response format
            return TranscriptResponse(
                video_id=video_id,
                title=result["title"],
                channel=result["channel"],
                duration=result["duration"],
                language=result["language"],
                segments=result["segments"],
                timestamp=datetime.now(),
                cached=False,
                backend_used=result.get("backend_used"),
                backend_info=result.get("backend_info"),
                available_languages=result.get("available_languages", [])
            )
                
        except Exception as e:
            self.logger.error(f"Error getting transcript for {video_id}: {str(e)}")
            raise Exception(f"Failed to get transcript: {str(e)}")
    
    async def get_available_languages(
        self, 
        video_id: str,
        backend: Optional[str] = None
    ) -> List[str]:
        """Get available languages for a video"""
        preferred_backend = None
        if backend:
            try:
                preferred_backend = BackendType(backend)
            except ValueError:
                self.logger.warning(f"Invalid backend specified: {backend}")
        
        try:
            return await self.backend_manager.get_available_languages(
                video_id=video_id,
                preferred_backend=preferred_backend
            )
        except Exception as e:
            self.logger.error(f"Error getting available languages for {video_id}: {str(e)}")
            return []
    
    def get_backend_status(self) -> Dict:
        """Get status of all available backends"""
        return self.backend_manager.get_backend_status()


transcript_service = TranscriptService()