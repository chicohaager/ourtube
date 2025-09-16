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
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

### Testing
```bash
# Backend API validation
cd backend
python test_endpoints.py
```

## Architecture

### Backend (`/backend`)
- **Framework**: FastAPI with Python 3.12
- **Entry Point**: `main.py`
- **Key Features**:
  - REST API endpoints under `/api/*`
  - WebSocket at `/ws` for real-time download progress
  - yt-dlp integration with automatic updates
  - Concurrent download management with semaphores
  - Static file serving for production frontend
  - Redis/Celery integration for task management
  - Security middleware in `security_config.py`

### Frontend (`/frontend`)
- **Framework**: React 18 + TypeScript + Vite
- **UI**: Material-UI (MUI) v6
- **State**: Zustand store in `src/store/downloadStore.ts`
- **API Client**: Axios-based in `src/api/index.ts`
- **WebSocket**: Custom hook in `src/hooks/useWebSocket.ts`
- **Types**: Comprehensive TypeScript definitions in `src/types/index.ts`
- **i18n**: German/English support in `src/i18n/locales/`

### Communication Flow
1. Frontend makes API calls to backend via Vite proxy (dev) or direct (prod)
2. Backend processes download requests using yt-dlp
3. Real-time progress updates sent via WebSocket
4. Frontend updates UI based on WebSocket messages

## Key Development Patterns

- Use async/await throughout backend code
- Follow existing Material-UI component patterns in frontend
- Maintain TypeScript compliance (note: strict mode currently disabled)
- WebSocket messages follow established format in `types/index.ts`
- Environment variables for configuration (see Docker Compose for examples)
- Rate limiting configured at 100 requests/60 seconds
- Path traversal protection implemented in download paths

## Docker Configuration

- **Development**: `docker-compose.yml` - Single service with Redis
- **Production**: `docker-compose.prod.yml` - Includes Nginx, SSL support
- **Volumes**: `/downloads` and `/config` for persistent data
- **Concurrent Downloads**: 3 (dev) / 5 (prod)

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-publish.yml`) handles:
- Multi-platform builds (amd64, arm64)
- Automated Docker Hub deployment
- Branch and tag-based deployments

## Security Considerations

- Security headers middleware configured
- Input validation for URLs and paths
- Rate limiting enabled
- CORS configuration (review for production)
- Trusted host middleware active