# OurTube - Modern Video & Audio Downloader

A modern, full-stack web application for downloading videos and audio from YouTube and 1000+ other platforms. Built with React, FastAPI, and yt-dlp.

![OurTube Logo](logo.png)

## ✨ Features

### 🎯 Core Functionality
- **Multi-platform support**: YouTube and 1000+ other video sites via yt-dlp
- **Video & Audio downloads**: Full video or audio-only with format selection
- **Quality selection**: Choose from Best, 4K, 1440p, 1080p, 720p, 480p, 360p, or lowest
- **Audio format options**: MP3, FLAC, OGG, M4A, WAV, AAC, OPUS with quality optimization
- **Real-time progress**: Live download progress with green progress bars, speed and ETA display
- **Concurrent downloads**: Up to 3 simultaneous downloads with queue management

### 🎨 User Experience
- **Modern UI**: Clean, responsive design with Material-UI components
- **Multilingual**: Full German/English localization with easy language switching
- **Video preview**: Thumbnail preview with video information before download
- **Dark/Light mode**: Automatic theme detection with manual toggle
- **Download history**: Persistent download history with status tracking

### ⚡ Performance & Reliability
- **Fast video info**: Optimized API with caching for quick video information retrieval (0.04s cached)
- **Thumbnail proxy**: CORS-free thumbnail loading via backend proxy
- **Auto-updates**: Automatic yt-dlp updates for latest platform support
- **Error handling**: Comprehensive error handling with user-friendly messages
- **Logging**: Detailed logging for debugging and monitoring

## Tech Stack

- **Backend**: FastAPI, yt-dlp, WebSockets
- **Frontend**: React, TypeScript, Material-UI, Zustand
- **Deployment**: Docker, Docker Compose

## Quick Start

### Using Docker (Recommended)

```bash
docker-compose up -d
```

Access the app at http://localhost:8000

### Manual Setup

1. **Backend**:
```bash
cd backend
pip install -r requirements.txt
python main.py
```

2. **Frontend**:
```bash
cd frontend
npm install
npm run dev
```

## Configuration

See [backend/FEATURES.md](backend/FEATURES.md) for detailed configuration options and advanced features.

Key environment variables:
- `DOWNLOAD_DIR`: Directory for downloads (default: `./downloads`)
- `MAX_CONCURRENT_DOWNLOADS`: Maximum concurrent downloads (default: 3)
- `PROXY`: HTTP/HTTPS/SOCKS proxy URL
- `YTDL_UPDATE_INTERVAL`: Auto-update interval in seconds (default: 86400)
- `OUTPUT_TEMPLATE`: yt-dlp filename template (default: `%(title)s.%(ext)s`)

## API Endpoints

- `POST /api/download` - Start a new download
- `GET /api/downloads` - List all downloads
- `GET /api/download/{id}` - Get download status
- `DELETE /api/download/{id}` - Cancel download
- `GET /api/info?url=` - Get video information
- `WS /ws` - WebSocket for real-time updates

## Development

```bash
# Backend development
cd backend
uvicorn main:app --reload

# Frontend development
cd frontend
npm run dev
```

## License

MIT