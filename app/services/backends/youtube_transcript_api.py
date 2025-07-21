from typing import List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, 
    NoTranscriptFound, 
    VideoUnavailable
)
import yt_dlp
from app.models import TranscriptSegment
from .base import TranscriptBackend, BackendInfo


class YouTubeTranscriptApiBackend(TranscriptBackend):
    """Backend using youtube-transcript-api library"""
    
    def __init__(self):
        super().__init__()
        self._api = YouTubeTranscriptApi()
    
    @property
    def backend_info(self) -> BackendInfo:
        return BackendInfo(
            name="youtube-transcript-api",
            version="0.6.2",
            capabilities={
                "manual_transcripts": True,
                "auto_transcripts": True,
                "language_translation": True,
                "multiple_formats": True,
                "proxy_support": True
            }
        )
    
    async def get_transcript(
        self, 
        video_id: str, 
        language: str = "en"
    ) -> Dict[str, Any]:
        """Extract transcript using youtube-transcript-api"""
        
        try:
            # Get video metadata using yt-dlp (lightweight extraction)
            metadata = await self._get_video_metadata(video_id)
            
            # Get available transcript languages
            available_languages = await self.get_available_languages(video_id)
            self.logger.info(f"Available languages: {available_languages}")
            
            # Try to get transcript in requested language
            transcript_data = None
            actual_language = language
            
            # First try exact language match
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
                actual_language = language
            except (NoTranscriptFound, Exception):
                # If Chinese language requested, try variations
                if language in ['zh-CN', 'zh-Hans', 'zh-cn']:
                    chinese_variants = self.get_chinese_language_variants()
                    for variant in chinese_variants:
                        if variant in available_languages:
                            try:
                                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[variant])
                                actual_language = variant
                                self.logger.info(f"Found Chinese transcript with language code: {variant}")
                                break
                            except (NoTranscriptFound, Exception):
                                continue
                
                # If still no transcript, try English as fallback
                if not transcript_data and 'en' in available_languages and language != 'en':
                    try:
                        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                        actual_language = 'en'
                        self.logger.info("Using English transcript as fallback")
                    except (NoTranscriptFound, Exception):
                        pass
            
            if not transcript_data:
                raise Exception(f"No transcript available for language: {language}. Available languages: {available_languages}")
            
            # Convert to our segment format
            segments = self._convert_to_segments(transcript_data)
            
            return {
                "title": metadata["title"],
                "channel": metadata["channel"],
                "duration": metadata["duration"],
                "language": actual_language,
                "segments": segments,
                "available_languages": available_languages
            }
            
        except (TranscriptsDisabled, VideoUnavailable) as e:
            self.logger.error(f"Video {video_id} unavailable or transcripts disabled: {str(e)}")
            raise Exception(f"Video unavailable or transcripts disabled: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error getting transcript for {video_id}: {str(e)}")
            raise Exception(f"Failed to get transcript: {str(e)}")
    
    async def get_available_languages(self, video_id: str) -> List[str]:
        """Get available language codes using youtube-transcript-api"""
        try:
            # Use static method to list transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            languages = []
            
            # Get all available transcripts
            for transcript in transcript_list:
                languages.append(transcript.language_code)
                # Also add generated transcript languages if available
                if hasattr(transcript, 'translation_languages_dict'):
                    for lang_code in transcript.translation_languages_dict.keys():
                        if lang_code not in languages:
                            languages.append(lang_code)
            
            return languages
            
        except Exception as e:
            self.logger.error(f"Error getting available languages for {video_id}: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if youtube-transcript-api is available"""
        try:
            # Try to import and create instance
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            return True
        except ImportError:
            return False
        except Exception:
            return False
    
    async def _get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Get video metadata using yt-dlp (faster than youtube-transcript-api for metadata)"""
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                info = ydl.extract_info(video_url, download=False)
                
                return {
                    "title": info.get('title', 'Unknown'),
                    "channel": info.get('uploader', 'Unknown'),
                    "duration": info.get('duration', 0)
                }
        except Exception as e:
            self.logger.warning(f"Could not get metadata for {video_id}: {str(e)}")
            return {
                "title": "Unknown",
                "channel": "Unknown", 
                "duration": 0
            }
    
    def _convert_to_segments(self, transcript_data: List[Dict]) -> List[TranscriptSegment]:
        """Convert youtube-transcript-api format to our TranscriptSegment format"""
        segments = []
        
        for item in transcript_data:
            # youtube-transcript-api provides: text, start, duration
            segment = TranscriptSegment(
                text=item.get('text', '').strip(),
                start=float(item.get('start', 0)),
                duration=float(item.get('duration', 0))
            )
            if segment.text:  # Only add non-empty segments
                segments.append(segment)
        
        return segments