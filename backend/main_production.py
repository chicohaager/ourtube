"""
OurTube Production Backend with Enhanced Security and Error Handling
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import yt_dlp
import json
from threading import Lock
import sys

# Import configurations
from security_config import setup_security, validate_url, validate_path

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.getenv("LOG_FILE", "./logs/ourtube.log"))
    ]
)
logger = logging.getLogger(__name__)

# Environment variables with validation
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
ENABLE_YTDL_UPDATE = os.getenv("ENABLE_YTDL_UPDATE", "true").lower() == "true"
OUTPUT_TEMPLATE = os.getenv("OUTPUT_TEMPLATE", "%(title)s.%(ext)s")
PROXY = os.getenv("PROXY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Validate configuration
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    logger.info(f"Created download directory: {DOWNLOAD_DIR}")

if MAX_CONCURRENT_DOWNLOADS < 1 or MAX_CONCURRENT_DOWNLOADS > 10:
    raise ValueError("MAX_CONCURRENT_DOWNLOADS must be between 1 and 10")

# Global state
downloads: Dict[str, any] = {}
active_downloads = 0
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
downloads_lock = Lock()

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            if conn in self.active_connections:
                self.disconnect(conn)

manager = ConnectionManager()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting OurTube in {ENVIRONMENT} mode")
    
    # Check ffmpeg
    from backend.main import check_ffmpeg_on_startup
    await check_ffmpeg_on_startup()
    
    # Auto-update yt-dlp if enabled
    if ENABLE_YTDL_UPDATE and ENVIRONMENT == "production":
        try:
            logger.info("Checking for yt-dlp updates...")
            yt_dlp.update()
        except Exception as e:
            logger.warning(f"Failed to update yt-dlp: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OurTube")

# Create FastAPI app
app = FastAPI(
    title="OurTube API",
    version="1.0.0",
    docs_url="/api/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Setup security
app = setup_security(app)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if ENVIRONMENT == "production" else str(exc)
        }
    )

# Import all endpoints from main.py
# (In production, you would import these properly)
from backend.main import (
    DownloadRequest, DownloadStatus, download_video,
    get_all_downloads, get_download, cancel_download,
    get_video_info, get_config, set_download_dir,
    open_download_dir, update_ytdlp_manual, get_formats,
    websocket_endpoint
)

# Register endpoints with additional validation
@app.post("/api/download")
async def create_download_secure(request: DownloadRequest):
    """Create a new download with security validation"""
    # Validate URL
    if not validate_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid or forbidden URL")
    
    # Call original endpoint
    return await download_video(request)

@app.post("/api/set-download-dir")
async def set_download_dir_secure(request: dict):
    """Set download directory with path validation"""
    directory = request.get("directory", "")
    
    # Validate path
    if not validate_path(directory):
        raise HTTPException(status_code=400, detail="Invalid directory path")
    
    # Call original endpoint
    return await set_download_dir(request)

# Register all other endpoints
app.get("/api/downloads")(get_all_downloads)
app.get("/api/download/{download_id}")(get_download)
app.delete("/api/download/{download_id}")(cancel_download)
app.get("/api/info")(get_video_info)
app.get("/api/config")(get_config)
app.post("/api/open-download-dir")(open_download_dir)
app.post("/api/update-ytdlp")(update_ytdlp_manual)
app.get("/api/formats")(get_formats)
app.websocket("/ws")(websocket_endpoint)

# Health check with monitoring
@app.get("/api/health")
async def health_check():
    """Enhanced health check endpoint"""
    try:
        # Check critical components
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": ENVIRONMENT,
            "downloads_active": active_downloads,
            "websocket_connections": len(manager.active_connections),
            "disk_space": check_disk_space(),
            "yt_dlp_version": yt_dlp.version.__version__,
        }
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

def check_disk_space():
    """Check available disk space"""
    import shutil
    stat = shutil.disk_usage(DOWNLOAD_DIR)
    return {
        "total_gb": round(stat.total / (1024**3), 2),
        "used_gb": round(stat.used / (1024**3), 2),
        "free_gb": round(stat.free / (1024**3), 2),
        "percent_used": round((stat.used / stat.total) * 100, 2)
    }

# Serve frontend in production
if os.path.exists("./frontend/dist"):
    app.mount("/assets", StaticFiles(directory="./frontend/dist/assets"), name="assets")
    
    @app.get("/")
    async def serve_spa():
        return FileResponse('./frontend/dist/index.html')
    
    @app.get("/{path:path}")
    async def serve_spa_fallback(path: str):
        if path.startswith("api/") or path == "ws":
            raise HTTPException(status_code=404, detail="Not found")
        
        file_path = f"./frontend/dist/{path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        return FileResponse('./frontend/dist/index.html')

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_production:app",
        host="0.0.0.0",
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "handlers": ["default"],
            },
        }
    )