import yt_dlp
import re
from typing import Optional, Dict, List
from datetime import datetime
from app.models import TranscriptResponse, TranscriptSegment, ErrorResponse
import logging


class TranscriptService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_video_id(self, url: str) -> str:
        youtube_regex = re.compile(
            r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
        )
        match = youtube_regex.search(url)
        if match:
            return match.group(1)
        raise ValueError("Invalid YouTube URL")
    
    async def get_transcript(self, video_id: Optional[str] = None, 
                           url: Optional[str] = None, 
                           language: str = "en") -> TranscriptResponse:
        if not video_id and not url:
            raise ValueError("Either video_id or url must be provided")
        
        if url and not video_id:
            video_id = self.extract_video_id(url)
        
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
                
                # Log available languages for debugging
                self.logger.info(f"Available manual subtitles: {list(subtitles.keys())}")
                self.logger.info(f"Available auto captions: {list(auto_subtitles.keys())}")
                
                # Try to get subtitles in the specified language
                subtitle_data = subtitles.get(language) or auto_subtitles.get(language)
                
                # If Chinese language not found, try common Chinese language code variations
                if not subtitle_data and language in ['zh-CN', 'zh-Hans', 'zh-cn']:
                    chinese_codes = ['zh-Hans', 'zh-CN', 'zh-cn', 'zh', 'chi', 'cmn']
                    for code in chinese_codes:
                        subtitle_data = subtitles.get(code) or auto_subtitles.get(code)
                        if subtitle_data:
                            language = code
                            self.logger.info(f"Found Chinese subtitles with code: {code}")
                            break
                
                if not subtitle_data:
                    # Try English as fallback
                    subtitle_data = subtitles.get('en') or auto_subtitles.get('en')
                    if subtitle_data:
                        language = 'en'
                        self.logger.info("Using English subtitles as fallback")
                
                if not subtitle_data:
                    raise Exception(f"No transcripts available for language: {language}. Available languages: {list(set(list(subtitles.keys()) + list(auto_subtitles.keys())))}")
                
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
                
                return TranscriptResponse(
                    video_id=video_id,
                    title=title,
                    channel=channel,
                    duration=duration,
                    language=language,
                    segments=segments,
                    timestamp=datetime.now(),
                    cached=False
                )
                
        except Exception as e:
            self.logger.error(f"Error getting transcript for {video_id}: {str(e)}")
            raise Exception(f"Failed to get transcript: {str(e)}")
    
    async def _parse_subtitles(self, ydl, subtitle_url: str) -> List[TranscriptSegment]:
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
        # Parse timestamp format: 00:00:01.000
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


transcript_service = TranscriptService()