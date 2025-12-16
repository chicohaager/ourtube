# OurTube - Modern Video & Audio Downloader

A modern, full-stack web application for downloading videos and audio from YouTube and 1000+ other platforms. Built with React, FastAPI, and yt-dlp.

![OurTube Logo](logo.png)

## Features

### Core Functionality
- **Multi-platform support**: YouTube and 1000+ other video sites via yt-dlp
- **Video & Audio downloads**: Full video or audio-only with format selection
- **Quality selection**: Best, 4K, 1440p, 1080p, 720p, 480p, 360p, or lowest
- **Audio formats**: MP3, FLAC, OGG, M4A, WAV, AAC, OPUS
- **Real-time progress**: Live download progress with speed and ETA
- **Concurrent downloads**: Configurable simultaneous downloads with queue management
- **Scheduled downloads**: Schedule downloads for later
- **Auto-retry**: Automatic retry on failure with configurable attempts
- **Subtitles**: Download subtitles in multiple languages

### User Experience
- **Modern UI**: Clean, responsive Material-UI design
- **Multilingual**: German/English localization
- **Video preview**: Thumbnail and info before download
- **Dark/Light mode**: Automatic detection with manual toggle
- **Download presets**: Save and reuse download configurations
- **Download history**: Persistent history with status tracking

### Performance & Security
- **Caching**: Fast video info retrieval with caching
- **Rate limiting**: Built-in request rate limiting
- **Security headers**: XSS, CSRF protection headers
- **Auto-updates**: Automatic yt-dlp updates
- **ffmpeg integration**: Audio extraction and format conversion

## Tech Stack

- **Backend**: FastAPI (Python 3.12), yt-dlp, WebSockets
- **Frontend**: React 18, TypeScript, Material-UI v6, Zustand
- **Deployment**: Docker, Docker Compose

## Quick Start

### Docker (Recommended)

```bash
docker-compose up -d
```

Access at http://localhost:8000

### ZimaOS / CasaOS

Use `docker-compose.zimaos.yml` for optimized ZimaOS deployment with FileBrowser integration.

### Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (development)
cd frontend
npm install
npm run dev
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_DIR` | `./downloads` | Download directory |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Simultaneous downloads |
| `PROXY` | - | HTTP/HTTPS/SOCKS proxy URL |
| `YTDL_UPDATE_INTERVAL` | `86400` | yt-dlp update interval (seconds) |
| `ENABLE_YTDL_UPDATE` | `true` | Enable automatic yt-dlp updates |
| `OUTPUT_TEMPLATE` | `%(title)s.%(ext)s` | Filename template |
| `HISTORY_FILE` | `./download_history.json` | Download history path |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |

See [backend/FEATURES.md](backend/FEATURES.md) for advanced configuration.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/download` | POST | Start download |
| `/api/downloads` | GET | List downloads |
| `/api/downloads` | DELETE | Clear history |
| `/api/download/{id}` | GET | Get status |
| `/api/download/{id}` | DELETE | Cancel download |
| `/api/info?url=` | GET | Get video info |
| `/api/formats?url=` | GET | Get available formats |
| `/api/config` | GET | Server configuration |
| `/api/update-ytdlp` | POST | Trigger yt-dlp update |
| `/ws` | WebSocket | Real-time progress |

## Development

```bash
# Backend with auto-reload
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend development server
cd frontend
npm run dev

# Build frontend for production
npm run build
```

## Requirements

- Python 3.12+
- Node.js 18+
- ffmpeg (for audio extraction and some video formats)

## License

MIT