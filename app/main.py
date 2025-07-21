from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager
from app.routers import transcript
from app.services.cache_service import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting YouTube Transcript API...")
    
    # Connect to Redis cache
    await cache_service.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down YouTube Transcript API...")
    await cache_service.disconnect()


app = FastAPI(
    title="YouTube Transcript API",
    description="A RESTful API to fetch YouTube video transcripts using yt-dlp",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcript.router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger(__name__)
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "YouTube Transcript API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/transcript/health",
            "get_by_id": "/api/v1/transcript/{video_id}",
            "get_by_url": "/api/v1/transcript/?url={youtube_url}",
            "post_request": "/api/v1/transcript/",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "YouTube Transcript API"}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True
    )