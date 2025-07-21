from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime


class TranscriptRequest(BaseModel):
    url: Optional[HttpUrl] = None
    video_id: Optional[str] = None
    language: Optional[str] = "en"
    backend: Optional[str] = None  # Optional backend preference


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
    backend_used: Optional[str] = None  # Which backend was used
    backend_info: Optional[Dict[str, Any]] = None  # Backend metadata
    available_languages: Optional[List[str]] = None  # Available languages for this video


class ErrorResponse(BaseModel):
    error: str
    message: str
    video_id: Optional[str] = None
    backend_used: Optional[str] = None


class BackendStatusResponse(BaseModel):
    backends: Dict[str, Any]
    primary: str
    fallback: str