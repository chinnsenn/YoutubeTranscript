import yt_dlp
import re
from typing import List, Dict, Any
from app.models import TranscriptSegment
from .base import TranscriptBackend, BackendInfo


class YtDlpBackend(TranscriptBackend):
    """Backend using yt-dlp library (original implementation)"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def backend_info(self) -> BackendInfo:
        return BackendInfo(
            name="yt-dlp",
            version="2025.6.30",
            capabilities={
                "manual_transcripts": True,
                "auto_transcripts": True,
                "language_translation": False,
                "multiple_formats": True,
                "video_metadata": True,
                "robust_extraction": True
            }
        )
    
    async def get_transcript(
        self, 
        video_id: str, 
        language: str = "en"
    ) -> Dict[str, Any]:
        """Extract transcript using yt-dlp (refactored from original code)"""
        
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language],
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    raise Exception("Failed to extract video information")
                
                title = info.get('title', 'Unknown')
                channel = info.get('uploader', 'Unknown')
                duration = info.get('duration', 0)
                
                # Extract subtitles
                subtitles = info.get('subtitles', {})
                auto_subtitles = info.get('automatic_captions', {})
                
                # Get all available languages
                available_languages = list(set(list(subtitles.keys()) + list(auto_subtitles.keys())))
                
                # Log available languages for debugging
                self.logger.info(f"Available manual subtitles: {list(subtitles.keys())}")
                self.logger.info(f"Available auto captions: {list(auto_subtitles.keys())}")
                
                # Try to get subtitles in the specified language
                subtitle_data = subtitles.get(language) or auto_subtitles.get(language)
                actual_language = language
                
                # If Chinese language not found, try common Chinese language code variations
                if not subtitle_data and language in ['zh-CN', 'zh-Hans', 'zh-cn']:
                    chinese_codes = self.get_chinese_language_variants()
                    for code in chinese_codes:
                        subtitle_data = subtitles.get(code) or auto_subtitles.get(code)
                        if subtitle_data:
                            actual_language = code
                            self.logger.info(f"Found Chinese subtitles with code: {code}")
                            break
                
                if not subtitle_data:
                    # Try English as fallback
                    subtitle_data = subtitles.get('en') or auto_subtitles.get('en')
                    if subtitle_data:
                        actual_language = 'en'
                        self.logger.info("Using English subtitles as fallback")
                
                if not subtitle_data:
                    raise Exception(f"No transcripts available for language: {language}. Available languages: {available_languages}")
                
                # Get the subtitle URL (prefer vtt format)
                subtitle_url = None
                for sub in subtitle_data:
                    if sub.get('ext') == 'vtt':
                        subtitle_url = sub.get('url')
                        break
                
                if not subtitle_url and subtitle_data:
                    subtitle_url = subtitle_data[0].get('url')
                
                if not subtitle_url:
                    raise Exception("No subtitle URL found")
                
                # Download and parse subtitles
                segments = await self._parse_subtitles(ydl, subtitle_url)
                
                return {
                    "title": title,
                    "channel": channel,
                    "duration": duration,
                    "language": actual_language,
                    "segments": segments,
                    "available_languages": available_languages
                }
                
        except Exception as e:
            self.logger.error(f"Error getting transcript for {video_id}: {str(e)}")
            raise Exception(f"Failed to get transcript: {str(e)}")
    
    async def get_available_languages(self, video_id: str) -> List[str]:
        """Get available language codes using yt-dlp"""
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    return []
                
                subtitles = info.get('subtitles', {})
                auto_subtitles = info.get('automatic_captions', {})
                
                # Combine both manual and auto-generated subtitle languages
                available_languages = list(set(list(subtitles.keys()) + list(auto_subtitles.keys())))
                return available_languages
                
        except Exception as e:
            self.logger.error(f"Error getting available languages for {video_id}: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if yt-dlp is available"""
        try:
            import yt_dlp
            return True
        except ImportError:
            return False
        except Exception:
            return False
    
    async def _parse_subtitles(self, ydl, subtitle_url: str) -> List[TranscriptSegment]:
        """Parse subtitle content from VTT format (from original implementation)"""
        try:
            # Download subtitle content
            subtitle_content = ydl.urlopen(subtitle_url).read().decode('utf-8')
            
            segments = []
            lines = subtitle_content.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines and WEBVTT headers
                if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
                    i += 1
                    continue
                
                # Look for timestamp line (format: 00:00:01.000 --> 00:00:03.000)
                if '-->' in line:
                    time_parts = line.split(' --> ')
                    if len(time_parts) == 2:
                        start_time = self._parse_timestamp(time_parts[0])
                        end_time = self._parse_timestamp(time_parts[1])
                        
                        # Get the text (next non-empty lines)
                        i += 1
                        text_lines = []
                        while i < len(lines) and lines[i].strip():
                            text_line = lines[i].strip()
                            # Remove HTML tags and positioning info
                            text_line = re.sub(r'<[^>]+>', '', text_line)
                            text_line = re.sub(r'\{[^}]+\}', '', text_line)
                            if text_line:
                                text_lines.append(text_line)
                            i += 1
                        
                        if text_lines:
                            text = ' '.join(text_lines)
                            duration = end_time - start_time
                            
                            segments.append(TranscriptSegment(
                                text=text,
                                start=start_time,
                                duration=duration
                            ))
                    else:
                        i += 1
                else:
                    i += 1
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Error parsing subtitles: {str(e)}")
            raise Exception(f"Failed to parse subtitles: {str(e)}")
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse timestamp format: 00:00:01.000 (from original implementation)"""
        timestamp = timestamp.strip()
        time_parts = timestamp.split(':')
        
        if len(time_parts) == 3:
            hours = float(time_parts[0])
            minutes = float(time_parts[1])
            seconds = float(time_parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(time_parts) == 2:
            minutes = float(time_parts[0])
            seconds = float(time_parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_parts[0])