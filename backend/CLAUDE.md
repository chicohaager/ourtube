ls -la# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Backend
```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

This is a FastAPI-based video downloader backend that integrates with yt-dlp. Key components:

1. **FastAPI Application** (`main.py`): REST API and WebSocket server
   - Download management endpoints (`/api/download`, `/api/downloads`)
   - Video info extraction (`/api/info`)
   - WebSocket for real-time progress updates (`/ws`)
   - Static file serving for frontend (if built)

2. **Core Features**:
   - Async download processing using `asyncio`
   - Real-time progress tracking via WebSockets
   - Support for audio-only downloads with MP3 conversion
   - Playlist download support
   - Download queue management with unique IDs

3. **Key Classes**:
   - `DownloadRequest`: Pydantic model for download requests
   - `DownloadStatus`: Tracks download state and progress
   - `ConnectionManager`: Manages WebSocket connections for broadcasting
   - `DownloadProgress`: yt-dlp progress hook handler

4. **Dependencies**:
   - `yt-dlp`: Core download functionality
   - `fastapi`: Web framework
   - `uvicorn`: ASGI server
   - `websockets`: Real-time communication
   - `redis` & `celery`: Installed but not currently used

## Important Notes

- Downloads are stored in `./downloads` directory by default
- The backend serves the frontend from `./frontend/dist` if it exists
- All download operations run in thread pool executor to avoid blocking
- CORS is configured to allow all origins (consider restricting in production)