# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**IMPORTANT**: This directory (`/home/holgi/dev/Ourtube/ourtube/`) contains only empty directory structure. The actual OurTube application codebase is located in the parent directory: `/home/holgi/dev/Ourtube/`

The active project structure is:
- `/home/holgi/dev/Ourtube/backend/` - FastAPI backend with yt-dlp integration
- `/home/holgi/dev/Ourtube/frontend/` - React TypeScript frontend with Material-UI
- `/home/holgi/dev/Ourtube/docker-compose.yml` - Docker deployment configuration

## Commands for Active Development

When working on the actual OurTube project, navigate to `/home/holgi/dev/Ourtube/` and use:

### Backend (FastAPI + Python)
```bash
cd /home/holgi/dev/Ourtube/backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React + TypeScript)
```bash
cd /home/holgi/dev/Ourtube/frontend
npm install
npm run dev  # Development server on port 3000
npm run build  # Production build
npm run lint  # ESLint (v9 migration needed)
```

### Full Application
```bash
cd /home/holgi/dev/Ourtube
docker-compose up -d  # Production deployment
docker-compose down   # Stop services
```

## Architecture Overview

OurTube is a video downloader application with:

- **Backend**: FastAPI with WebSocket support for real-time download progress
- **Frontend**: React 18 + TypeScript + Material-UI with Zustand state management
- **Core**: yt-dlp integration supporting 1000+ video sites
- **Features**: Concurrent downloads, audio conversion, proxy support, download history

## Key Integration Points

- WebSocket endpoint `/ws` for real-time progress updates
- REST API at `/api/*` for download management and metadata
- Vite proxy configuration routes frontend API calls to backend:8000
- Download files served from backend's `downloads/` directory

## Development Notes

- Backend uses extensive environment variable configuration
- Frontend proxy in `vite.config.ts` handles API routing during development
- ESLint v9 migration is pending (noted in package.json)
- Project includes optimization variants (`*_optimized.*` files)

If you need to work on this empty subdirectory specifically, please clarify the intended purpose as it currently contains no functional code.