from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.models import TranscriptSegment
import logging


class BackendInfo:
    """Information about a transcript extraction backend"""
    def __init__(self, name: str, version: str, capabilities: Dict[str, Any]):
        self.name = name
        self.version = version
        self.capabilities = capabilities


class TranscriptBackend(ABC):
    """Abstract base class for transcript extraction backends"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def backend_info(self) -> BackendInfo:
        """Return information about this backend"""
        pass
    
    @abstractmethod
    async def get_transcript(
        self, 
        video_id: str, 
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Extract transcript for a YouTube video
        
        Args:
            video_id: YouTube video ID
            language: Language code for transcript
            
        Returns:
            Dict containing:
            - title: Video title
            - channel: Channel name
            - duration: Video duration in seconds
            - language: Actual language code used
            - segments: List of TranscriptSegment objects
            - available_languages: List of available language codes
            
        Raises:
            Exception: If transcript extraction fails
        """
        pass
    
    @abstractmethod
    async def get_available_languages(self, video_id: str) -> List[str]:
        """
        Get list of available language codes for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of available language codes
            
        Raises:
            Exception: If language detection fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available and functional"""
        pass
    
    def normalize_language_code(self, language: str) -> str:
        """
        Normalize language code to common format
        Override in subclasses for backend-specific normalization
        """
        return language.lower()
    
    def get_chinese_language_variants(self) -> List[str]:
        """Get list of Chinese language code variants to try"""
        return ['zh-Hans', 'zh-CN', 'zh-cn', 'zh', 'chi', 'cmn', 'zh-Hant', 'zh-TW']