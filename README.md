# YouTube Transcript API

A RESTful API service for fetching YouTube video transcripts using yt-dlp, built with FastAPI and Redis caching.

## Features

- 🎥 Extract transcripts from YouTube videos
- 🌍 Support for multiple languages
- ⚡ Redis caching for improved performance
- 🐳 Docker containerization with docker-compose
- 📖 Interactive API documentation (Swagger UI)
- 🔍 RESTful endpoints for easy integration

## Quick Start

### Using Docker Compose (Recommended)

1. Clone and navigate to the project:
```bash
git clone <repository-url>
cd YoutubeTranscript
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access the API:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis (optional, for caching):
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

3. Run the application:
```bash
cd app
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Get Transcript by Video ID
```http
GET /api/v1/transcript/{video_id}?language=en
```

### Get Transcript by URL
```http
GET /api/v1/transcript/?url=https://www.youtube.com/watch?v=VIDEO_ID&language=en
```

### Get Transcript via POST
```http
POST /api/v1/transcript/
Content-Type: application/json

{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "language": "en"
}
```

### Cache Management
```http
GET /api/v1/transcript/cache/stats    # Get cache statistics
DELETE /api/v1/transcript/cache/clear  # Clear all cached transcripts
DELETE /api/v1/transcript/{video_id}/cache  # Clear specific cached transcript
```

## Configuration

Environment variables (see `.env` file):

- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 3600)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

## Architecture

```
YoutubeTranscript/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Pydantic data models
│   ├── services/
│   │   ├── transcript_service.py  # YouTube transcript extraction
│   │   └── cache_service.py       # Redis caching logic
│   └── routers/
│       └── transcript.py    # API route handlers
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Multi-service deployment
├── requirements.txt        # Python dependencies
└── .env                    # Environment configuration
```

## Development

### Running Tests
```bash
# Add your test commands here
```

### Building Docker Image
```bash
docker build -t youtube-transcript-api .
```

### Stopping Services
```bash
docker-compose down
```

## License

[Add your license information here]