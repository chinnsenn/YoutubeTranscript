from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
import re
from app.models import TranscriptResponse, TranscriptRequest, ErrorResponse
from app.services.transcript_service import transcript_service
from app.services.cache_service import cache_service
import logging

router = APIRouter(prefix="/api/v1/transcript", tags=["transcript"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    cache_stats = await cache_service.get_cache_stats()
    return {
        "status": "healthy",
        "service": "YouTube Transcript API",
        "cache": cache_stats
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return await cache_service.get_cache_stats()


@router.delete("/cache/clear")
async def clear_cache():
    """Clear all cached transcripts"""
    await cache_service.clear_all_cache()
    return {"message": "Cache cleared successfully"}


@router.get("/{video_id}", response_model=TranscriptResponse)
async def get_transcript_by_id(
    video_id: str = Path(..., description="YouTube video ID"),
    language: str = Query("en", description="Language code (e.g., en, es, fr)")
):
    """Get transcript by YouTube video ID"""
    
    # Validate video ID format
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        raise HTTPException(status_code=400, detail="Invalid YouTube video ID format")
    
    try:
        # Check cache first
        cached_transcript = await cache_service.get_transcript(video_id, language)
        if cached_transcript:
            return cached_transcript
        
        # Get transcript from YouTube
        transcript = await transcript_service.get_transcript(
            video_id=video_id, 
            language=language
        )
        
        # Cache the result
        await cache_service.set_transcript(video_id, language, transcript)
        
        return transcript
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting transcript for {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")


@router.get("/", response_model=TranscriptResponse)
async def get_transcript_by_url(
    url: str = Query(..., description="YouTube video URL"),
    language: str = Query("en", description="Language code (e.g., en, es, fr)")
):
    """Get transcript by YouTube video URL"""
    
    try:
        # Extract video ID from URL
        video_id = transcript_service.extract_video_id(url)
        
        # Check cache first
        cached_transcript = await cache_service.get_transcript(video_id, language)
        if cached_transcript:
            return cached_transcript
        
        # Get transcript from YouTube
        transcript = await transcript_service.get_transcript(
            url=url, 
            language=language
        )
        
        # Cache the result
        await cache_service.set_transcript(video_id, language, transcript)
        
        return transcript
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting transcript for URL {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")


@router.post("/", response_model=TranscriptResponse)
async def get_transcript_post(request: TranscriptRequest):
    """Get transcript via POST request with JSON body"""
    
    if not request.video_id and not request.url:
        raise HTTPException(status_code=400, detail="Either video_id or url must be provided")
    
    try:
        video_id = request.video_id
        if request.url and not video_id:
            video_id = transcript_service.extract_video_id(str(request.url))
        
        # Check cache first
        cached_transcript = await cache_service.get_transcript(video_id, request.language)
        if cached_transcript:
            return cached_transcript
        
        # Get transcript from YouTube
        transcript = await transcript_service.get_transcript(
            video_id=video_id,
            url=str(request.url) if request.url else None,
            language=request.language
        )
        
        # Cache the result
        await cache_service.set_transcript(video_id, request.language, transcript)
        
        return transcript
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")


@router.delete("/{video_id}/cache")
async def delete_cached_transcript(
    video_id: str = Path(..., description="YouTube video ID"),
    language: str = Query("en", description="Language code")
):
    """Delete cached transcript for specific video and language"""
    
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        raise HTTPException(status_code=400, detail="Invalid YouTube video ID format")
    
    await cache_service.delete_transcript(video_id, language)
    return {"message": f"Cached transcript for {video_id}:{language} deleted successfully"}