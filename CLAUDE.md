# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OurTube is a modern video downloader application that downloads videos from YouTube and 1000+ other sites using yt-dlp. It's a full-stack web application with React frontend and FastAPI backend, featuring real-time WebSocket communication for download progress updates.

## Commands

### Development
```bash
# Backend (FastAPI on port 8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (React on port 3000)
cd frontend
npm install
npm run dev
```

### Production
```bash
# Full application via Docker
docker-compose up -d

# Or use deployment script
./deploy.sh
```

### Frontend Commands
```bash
cd frontend
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

### Testing
```bash
cd backend
python test_endpoints.py  # Backend API validation
```

## Architecture

### Backend (`/backend`)
- **Framework**: FastAPI with Python 3.12
- **Entry Point**: `main.py` - contains all REST endpoints, WebSocket handler, and yt-dlp integration
- **Security**: `security_config.py` - middleware configuration
- **Key Classes**:
  - `DownloadRequest` / `DownloadStatus`: Pydantic models for API
  - `ConnectionManager`: WebSocket connection management
  - `DownloadProgress`: yt-dlp progress hook handler

### Frontend (`/frontend`)
- **Framework**: React 18 + TypeScript + Vite
- **UI**: Material-UI (MUI) v6
- **State Management**: Zustand
  - `src/store/downloadStore.ts` - download state
  - `src/store/settingsStore.ts` - app settings
- **API Client**: `src/api/index.ts` - Axios-based
- **WebSocket**: `src/hooks/useWebSocket.ts` - real-time updates
- **Types**: `src/types/index.ts` - TypeScript definitions
- **i18n**: `src/i18n/locales/` - German/English support

### API Endpoints
- `POST /api/download` - Start download
- `GET /api/downloads` - List all downloads
- `GET /api/download/{id}` - Get download status
- `DELETE /api/download/{id}` - Cancel download
- `GET /api/info?url=` - Get video information
- `GET /api/formats?url=` - Get available formats
- `GET /api/config` - Server configuration
- `POST /api/update-ytdlp` - Trigger yt-dlp update
- `WS /ws` - WebSocket for real-time progress

### Communication Flow
1. Frontend makes API calls to backend via Vite proxy (dev) or direct (prod)
2. Backend processes download requests using yt-dlp
3. Real-time progress updates sent via WebSocket
4. Frontend updates UI based on WebSocket messages

## Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_DIR` | `./downloads` | Download directory |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Simultaneous downloads limit |
| `PROXY` | None | HTTP/HTTPS/SOCKS proxy URL |
| `OUTPUT_TEMPLATE` | `%(title)s.%(ext)s` | yt-dlp filename template |
| `YTDL_UPDATE_INTERVAL` | `86400` | Auto-update interval (seconds) |
| `ENABLE_YTDL_UPDATE` | `true` | Enable automatic yt-dlp updates |
| `HISTORY_FILE` | `./download_history.json` | Path to persistent download history |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per rate limit window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

## Key Development Patterns

- Use async/await throughout backend code
- All download operations run in thread pool executor to avoid blocking
- Security middleware in `security_config.py` provides rate limiting and security headers
- Follow existing Material-UI component patterns in frontend
- TypeScript strict mode is currently disabled
- WebSocket messages follow established format in `types/index.ts`
- ffmpeg is required for audio extraction and some video formats

## Docker Configuration

- **Development**: `docker-compose.yml` - Main app with Redis (Redis included but not used)
- **Production**: `docker-compose.prod.yml` - Includes Nginx, SSL support
- **ZimaOS**: `docker-compose.zimaos.yml` - Optimized for ZimaOS/CasaOS with FileBrowser
- Access at http://localhost:8000 after `docker-compose up -d`

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-publish.yml`) handles:
- Multi-platform builds (amd64, arm64)
- Automated Docker Hub deployment