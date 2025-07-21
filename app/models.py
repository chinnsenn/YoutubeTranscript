from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
from datetime import datetime


class TranscriptRequest(BaseModel):
    url: Optional[HttpUrl] = None
    video_id: Optional[str] = None
    language: Optional[str] = "en"


class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptResponse(BaseModel):
    video_id: str
    title: str
    channel: str
    duration: float
    language: str
    segments: List[TranscriptSegment]
    timestamp: datetime
    cached: bool = False


class ErrorResponse(BaseModel):
    error: str
    message: str
    video_id: Optional[str] = None