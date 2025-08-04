from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Dict, List, Set
import yt_dlp
import asyncio
import os
import uuid
from datetime import datetime, timedelta
import json
import subprocess
import logging
from contextlib import asynccontextmanager
import sys
from functools import lru_cache
import aiofiles
from asyncio import Lock
import re
from urllib.parse import urlparse

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables with validation
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
OUTPUT_TEMPLATE = os.getenv("OUTPUT_TEMPLATE", "%(title)s.%(ext)s")
YTDL_UPDATE_INTERVAL = int(os.getenv("YTDL_UPDATE_INTERVAL", "86400"))  # 24 hours
PROXY = os.getenv("PROXY", None)
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
YTDL_OPTIONS = os.getenv("YTDL_OPTIONS", None)
ENABLE_YTDL_UPDATE = os.getenv("ENABLE_YTDL_UPDATE", "true").lower() == "true"
HISTORY_FILE = os.getenv("HISTORY_FILE", "./download_history.json")
MAX_HISTORY_SIZE = int(os.getenv("MAX_HISTORY_SIZE", "1000"))
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
MAX_URL_LENGTH = 2048
MAX_FILENAME_LENGTH = 255

# Validate configuration
if MAX_CONCURRENT_DOWNLOADS < 1 or MAX_CONCURRENT_DOWNLOADS > 10:
    raise ValueError("MAX_CONCURRENT_DOWNLOADS must be between 1 and 10")

# Global state with thread safety
active_downloads = 0
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
downloads_lock = Lock()
history_lock = Lock()

# Cache for expensive operations
@lru_cache(maxsize=100)
def is_valid_url(url: str) -> bool:
    """Validate URL format and scheme"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https'] and bool(parsed.netloc)
    except:
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    # Remove directory separators and null bytes
    filename = re.sub(r'[/\\:\0]', '_', filename)
    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        filename = name[:MAX_FILENAME_LENGTH - len(ext)] + ext
    return filename

async def update_ytdlp():
    """Update yt-dlp to the latest version with retry logic"""
    if not ENABLE_YTDL_UPDATE:
        return
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Updating yt-dlp (attempt {attempt + 1}/{max_retries})...")
            python_exec = sys.executable if hasattr(sys, 'executable') else 'python3'
            
            process = await asyncio.create_subprocess_exec(
                python_exec, "-m", "pip", "install", "--upgrade", "yt-dlp",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                if "Successfully installed" in stdout.decode():
                    logger.info("yt-dlp updated successfully")
                else:
                    logger.info("yt-dlp is already up to date")
                return
            else:
                logger.error(f"Failed to update yt-dlp: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error updating yt-dlp: {e}")
            
        if attempt < max_retries - 1:
            await asyncio.sleep(5)  # Wait before retry
    
    logger.error("Failed to update yt-dlp after all retries")

async def periodic_ytdlp_update():
    """Periodically update yt-dlp with jitter to avoid thundering herd"""
    while True:
        # Add random jitter (0-300 seconds) to avoid all instances updating at once
        jitter = asyncio.create_task(asyncio.sleep(YTDL_UPDATE_INTERVAL + (uuid.uuid4().int % 300)))
        await jitter
        await update_ytdlp()

async def periodic_history_save():
    """Periodically save download history with error handling"""
    while True:
        await asyncio.sleep(60)  # Save every minute
        try:
            await save_download_history()
        except Exception as e:
            logger.error(f"Failed to save history periodically: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied creating directories")
        raise
    
    # Load download history
    await load_download_history()
    
    # Background tasks
    background_tasks = []
    
    if ENABLE_YTDL_UPDATE:
        background_tasks.append(asyncio.create_task(periodic_ytdlp_update()))
    
    background_tasks.append(asyncio.create_task(periodic_history_save()))
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    
    # Final save with retry
    for _ in range(3):
        try:
            await save_download_history()
            break
        except Exception as e:
            logger.error(f"Failed to save history on shutdown: {e}")
            await asyncio.sleep(1)

app = FastAPI(
    title="OurTube",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable swagger in production
    redoc_url=None
)

# Security middleware
if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Check if ffmpeg is available
FFMPEG_AVAILABLE = False
try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    FFMPEG_AVAILABLE = True
    logger.info("ffmpeg is available")
except (subprocess.CalledProcessError, FileNotFoundError):
    logger.warning("ffmpeg not found. Some features will be unavailable.")

# CORS with specific origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ENV", "development") == "development" else ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    max_age=3600
)

class DownloadRequest(BaseModel):
    url: HttpUrl
    format: Optional[str] = Field(default="best", max_length=50)
    audio_only: Optional[bool] = False
    playlist: Optional[bool] = False
    output_dir: Optional[str] = Field(default=None, max_length=500)
    quality: Optional[str] = Field(default=None, pattern="^(144|240|360|480|720|1080|1440|2160)p?$")
    custom_args: Optional[str] = Field(default=None, max_length=1000)
    output_template: Optional[str] = Field(default=None, max_length=200)
    proxy: Optional[HttpUrl] = None
    
    @validator('url')
    def validate_url(cls, v):
        url_str = str(v)
        if len(url_str) > MAX_URL_LENGTH:
            raise ValueError(f'URL too long (max {MAX_URL_LENGTH} characters)')
        if not is_valid_url(url_str):
            raise ValueError('Invalid URL format')
        return v
    
    @validator('output_dir')
    def validate_output_dir(cls, v):
        if v and ('..' in v or v.startswith('/')):
            raise ValueError('Invalid output directory')
        return v
    
    @validator('custom_args')
    def validate_custom_args(cls, v):
        if v:
            try:
                json.loads(v)
            except json.JSONDecodeError:
                raise ValueError('custom_args must be valid JSON')
        return v

class DownloadStatus(BaseModel):
    id: str
    url: str
    status: str
    progress: Optional[float] = Field(default=0, ge=0, le=100)
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    size: Optional[int] = None
    speed: Optional[str] = None
    eta: Optional[str] = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients with error handling"""
        if not self.active_connections:
            return
            
        disconnected = set()
        async with self._lock:
            connections = list(self.active_connections)
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections -= disconnected

manager = ConnectionManager()
downloads: Dict[str, DownloadStatus] = {}

async def load_download_history():
    """Load download history from file with async I/O"""
    if not os.path.exists(HISTORY_FILE):
        return
        
    try:
        async with aiofiles.open(HISTORY_FILE, 'r') as f:
            content = await f.read()
            history_data = json.loads(content)
            
        async with downloads_lock:
            for item in history_data:
                # Convert datetime strings back to datetime objects
                if 'created_at' in item:
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                if 'completed_at' in item and item['completed_at']:
                    item['completed_at'] = datetime.fromisoformat(item['completed_at'])
                downloads[item['id']] = DownloadStatus(**item)
                
        logger.info(f"Loaded {len(downloads)} downloads from history")
    except Exception as e:
        logger.error(f"Failed to load download history: {e}")

async def save_download_history():
    """Save download history to file with async I/O and atomic write"""
    try:
        async with downloads_lock:
            # Convert to list and limit size
            history_list = list(downloads.values())
        
        # Sort by created_at (newest first) and limit
        history_list.sort(key=lambda x: x.created_at, reverse=True)
        history_list = history_list[:MAX_HISTORY_SIZE]
        
        # Convert to dict for JSON serialization
        history_data = []
        for item in history_list:
            item_dict = item.model_dump()
            # Convert datetime to ISO format
            if item_dict.get('created_at'):
                item_dict['created_at'] = item_dict['created_at'].isoformat()
            if item_dict.get('completed_at'):
                item_dict['completed_at'] = item_dict['completed_at'].isoformat()
            history_data.append(item_dict)
        
        # Atomic write with temporary file
        temp_file = f"{HISTORY_FILE}.tmp"
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(json.dumps(history_data, indent=2))
        
        # Atomic rename
        os.replace(temp_file, HISTORY_FILE)
        
    except Exception as e:
        logger.error(f"Failed to save download history: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

class DownloadProgress:
    def __init__(self, download_id: str, loop=None):
        self.download_id = download_id
        self.loop = loop
        self.last_update = 0
        self.update_interval = 0.5  # Throttle updates to every 0.5 seconds

    def __call__(self, d):
        current_time = asyncio.get_event_loop().time()
        
        if d['status'] == 'downloading':
            # Throttle progress updates
            if current_time - self.last_update < self.update_interval:
                return
                
            self.last_update = current_time
            
            progress = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
            downloads[self.download_id].progress = round(progress, 2)
            
            # Extract additional info
            if 'total_bytes' in d:
                downloads[self.download_id].size = d['total_bytes']
            if '_speed_str' in d:
                downloads[self.download_id].speed = d['_speed_str']
            if '_eta_str' in d:
                downloads[self.download_id].eta = d['_eta_str']
            
            # Schedule the broadcast in the main event loop
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({
                        "type": "progress",
                        "download_id": self.download_id,
                        "progress": downloads[self.download_id].progress,
                        "speed": downloads[self.download_id].speed,
                        "eta": downloads[self.download_id].eta,
                        "size": downloads[self.download_id].size
                    }), 
                    self.loop
                )
        elif d['status'] == 'finished':
            downloads[self.download_id].status = 'processing'
            filename = d.get('filename', '')
            if filename:
                downloads[self.download_id].filename = sanitize_filename(os.path.basename(filename))

def get_ydl_opts(request: DownloadRequest, download_id: str, loop=None):
    # Validate and use custom or default output directory
    output_dir = request.output_dir or DOWNLOAD_DIR
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(DOWNLOAD_DIR, output_dir)
    
    # Ensure directory is within allowed paths
    try:
        output_dir = os.path.realpath(output_dir)
        if not output_dir.startswith(os.path.realpath(DOWNLOAD_DIR)):
            output_dir = DOWNLOAD_DIR
    except:
        output_dir = DOWNLOAD_DIR
    
    # Use custom or default output template with sanitization
    template = request.output_template or OUTPUT_TEMPLATE
    # Basic template validation
    if '..' in template or template.startswith('/'):
        template = OUTPUT_TEMPLATE
    
    output_template = os.path.join(output_dir, template)
    
    opts = {
        'outtmpl': output_template,
        'progress_hooks': [DownloadProgress(download_id, loop)],
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'no_color': True,
        'no_call_home': True,
        'extract_flat': False,
        # Security options
        'restrictfilenames': True,  # Sanitize filenames
        'windowsfilenames': True,   # Compatible filenames
        'no_overwrites': True,      # Don't overwrite existing files
    }
    
    # Add proxy if specified
    if request.proxy or PROXY:
        proxy_url = str(request.proxy) if request.proxy else PROXY
        opts['proxy'] = proxy_url
    
    # Handle quality selection with validation
    if request.quality and not request.audio_only:
        height = request.quality.replace('p', '')
        if FFMPEG_AVAILABLE:
            opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
        else:
            opts['format'] = f'best[height<={height}]'
    elif request.audio_only:
        if not FFMPEG_AVAILABLE:
            raise ValueError("Audio-only downloads require ffmpeg to be installed")
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # Use best single file format to avoid ffmpeg requirement when not available
        if FFMPEG_AVAILABLE:
            opts['format'] = request.format if request.format != 'best' else 'best'
        else:
            # Without ffmpeg, prefer single file formats that don't need merging
            opts['format'] = 'best[ext=mp4]/best[ext=webm]/best'
    
    if not request.playlist:
        opts['noplaylist'] = True
    
    # Apply custom YTDL_OPTIONS from environment with validation
    if YTDL_OPTIONS:
        try:
            custom_opts = json.loads(YTDL_OPTIONS)
            # Whitelist safe options
            safe_keys = {'format', 'subtitleslangs', 'writesubtitles', 'writethumbnail'}
            custom_opts = {k: v for k, v in custom_opts.items() if k in safe_keys}
            opts.update(custom_opts)
        except json.JSONDecodeError:
            logger.error("Invalid YTDL_OPTIONS JSON")
    
    # Apply custom arguments from request with validation
    if request.custom_args:
        try:
            custom_args = json.loads(request.custom_args)
            # Whitelist safe options
            safe_keys = {'writesubtitles', 'writethumbnail', 'subtitleslangs'}
            custom_args = {k: v for k, v in custom_args.items() if k in safe_keys}
            opts.update(custom_args)
        except json.JSONDecodeError:
            logger.error("Invalid custom_args JSON")
    
    return opts

@app.post("/api/download", status_code=201)
async def create_download(request: DownloadRequest):
    global active_downloads
    
    # Check if we're at capacity
    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        # Count queued downloads
        async with downloads_lock:
            queued_count = sum(1 for d in downloads.values() if d.status == "queued")
        
        if queued_count > MAX_CONCURRENT_DOWNLOADS * 2:
            raise HTTPException(
                status_code=503,
                detail="Download queue is full. Please try again later."
            )
    
    download_id = str(uuid.uuid4())
    
    download_status = DownloadStatus(
        id=download_id,
        url=str(request.url),
        status="queued",
        created_at=datetime.now()
    )
    
    async with downloads_lock:
        downloads[download_id] = download_status
    
    asyncio.create_task(process_download(download_id, request))
    
    return {"download_id": download_id, "status": "queued"}

async def process_download(download_id: str, request: DownloadRequest):
    global active_downloads
    
    async with download_semaphore:  # Limit concurrent downloads
        try:
            active_downloads += 1
            
            async with downloads_lock:
                downloads[download_id].status = "downloading"
            
            await manager.broadcast({
                "type": "status",
                "download_id": download_id,
                "status": "downloading"
            })
            
            loop = asyncio.get_event_loop()
            
            # Validate options before starting download
            try:
                ydl_opts = get_ydl_opts(request, download_id, loop)
            except ValueError as e:
                raise Exception(str(e))
            
            # Run download with timeout
            timeout = 3600  # 1 hour timeout
            await asyncio.wait_for(
                loop.run_in_executor(None, download_with_ydl, str(request.url), ydl_opts, download_id),
                timeout=timeout
            )
            
            async with downloads_lock:
                downloads[download_id].status = "completed"
                downloads[download_id].completed_at = datetime.now()
                downloads[download_id].progress = 100
            
            await manager.broadcast({
                "type": "completed",
                "download_id": download_id,
                "filename": downloads[download_id].filename
            })
            
            # Save history after successful download
            asyncio.create_task(save_download_history())
            
        except asyncio.TimeoutError:
            async with downloads_lock:
                downloads[download_id].status = "failed"
                downloads[download_id].error = "Download timeout exceeded"
            await manager.broadcast({
                "type": "error",
                "download_id": download_id,
                "error": "Download timeout exceeded"
            })
            
        except Exception as e:
            error_msg = str(e)
            # Sanitize error message to avoid exposing internal details
            if "ffmpeg" in error_msg.lower():
                error_msg = "This operation requires ffmpeg to be installed"
            elif "private" in error_msg.lower():
                error_msg = "This video is private or restricted"
            elif "404" in error_msg:
                error_msg = "Video not found"
            else:
                error_msg = "Download failed. Please check the URL and try again."
            
            async with downloads_lock:
                downloads[download_id].status = "failed"
                downloads[download_id].error = error_msg
            
            await manager.broadcast({
                "type": "error",
                "download_id": download_id,
                "error": error_msg
            })
            
            # Save history after failed download too
            asyncio.create_task(save_download_history())
            
        finally:
            active_downloads -= 1

def download_with_ydl(url: str, opts: dict, download_id: str):
    """Execute download with yt-dlp"""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        # Re-raise with cleaner error message
        raise Exception(str(e))

@app.get("/api/downloads")
async def get_downloads(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None
):
    """Get downloads with pagination and filtering"""
    if limit > 1000:
        limit = 1000
    
    async with downloads_lock:
        all_downloads = list(downloads.values())
    
    # Filter by status if provided
    if status:
        all_downloads = [d for d in all_downloads if d.status == status]
    
    # Sort by created_at descending
    all_downloads.sort(key=lambda x: x.created_at, reverse=True)
    
    # Paginate
    total = len(all_downloads)
    paginated = all_downloads[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "downloads": paginated
    }

@app.get("/api/download/{download_id}")
async def get_download(download_id: str):
    async with downloads_lock:
        if download_id not in downloads:
            raise HTTPException(status_code=404, detail="Download not found")
        return downloads[download_id]

@app.delete("/api/download/{download_id}")
async def cancel_download(download_id: str):
    async with downloads_lock:
        if download_id not in downloads:
            raise HTTPException(status_code=404, detail="Download not found")
        
        if downloads[download_id].status in ["downloading", "queued"]:
            downloads[download_id].status = "cancelled"
            return {"message": "Download cancelled"}
    
    return {"message": "Cannot cancel completed download"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            # Could implement client commands here (e.g., subscribe to specific downloads)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)

@app.get("/api/info")
async def get_video_info(url: str, request: Request):
    """Get video information with caching"""
    # Validate URL
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=400, detail="URL too long")
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'no_color': True,
            'no_call_home': True,
        }
        
        if PROXY:
            ydl_opts['proxy'] = PROXY
        
        # Run with timeout
        loop = asyncio.get_event_loop()
        info = await asyncio.wait_for(
            loop.run_in_executor(None, extract_info_with_ydl, url, ydl_opts),
            timeout=30
        )
        
        return {
            "title": info.get('title', 'Unknown'),
            "duration": info.get('duration', 0),
            "thumbnail": info.get('thumbnail'),
            "uploader": info.get('uploader', 'Unknown'),
            "description": info.get('description', '')[:500],  # Limit description length
            "view_count": info.get('view_count', 0),
            "like_count": info.get('like_count', 0),
            "upload_date": info.get('upload_date'),
            "formats": [
                {
                    "format_id": f.get('format_id'),
                    "ext": f.get('ext'),
                    "quality": f.get('quality'),
                    "filesize": f.get('filesize'),
                    "resolution": f.get('resolution', 'audio only')
                }
                for f in info.get('formats', [])
                if f.get('format_id')
            ][:20]  # Limit formats returned
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        raise HTTPException(status_code=400, detail="Failed to retrieve video information")

def extract_info_with_ydl(url: str, opts: dict):
    """Extract video info with yt-dlp"""
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

@lru_cache(maxsize=1)
def get_ytdlp_version():
    """Get current yt-dlp version with caching"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else "Unknown"
    except:
        return "Not installed"

@app.get("/api/config")
async def get_config():
    """Get current configuration and server capabilities"""
    return {
        "ffmpeg_available": FFMPEG_AVAILABLE,
        "max_concurrent_downloads": MAX_CONCURRENT_DOWNLOADS,
        "active_downloads": active_downloads,
        "ytdl_auto_update": ENABLE_YTDL_UPDATE,
        "proxy_configured": PROXY is not None,
        "download_dir": os.path.basename(DOWNLOAD_DIR),  # Don't expose full path
        "output_template": OUTPUT_TEMPLATE,
        "supported_sites": "YouTube and 1000+ other sites via yt-dlp",
        "ytdlp_version": get_ytdlp_version(),
        "features": {
            "audio_only": FFMPEG_AVAILABLE,
            "quality_selection": True,
            "playlist_download": True,
            "subtitle_download": True,
            "thumbnail_download": True
        }
    }

@app.post("/api/update-ytdlp")
async def update_ytdlp_manual(request: Request):
    """Manually trigger yt-dlp update"""
    # Could add authentication here
    await update_ytdlp()
    # Clear version cache
    get_ytdlp_version.cache_clear()
    return {"message": "yt-dlp update triggered", "version": get_ytdlp_version()}

@app.get("/api/formats")
async def get_formats(url: str):
    """Get available formats for a video"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'listformats': True,
        }
        
        if PROXY:
            ydl_opts['proxy'] = PROXY
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        formats = []
        for f in info.get('formats', []):
            if f.get('format_id'):
                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution', 'audio only'),
                    'fps': f.get('fps'),
                    'filesize': f.get('filesize'),
                    'tbr': f.get('tbr'),  # Total bitrate
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                })
                
        return {
            "title": info.get('title'),
            "formats": formats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "downloads_active": active_downloads,
        "websocket_connections": len(manager.active_connections)
    }

# Frontend serving routes (must be last due to catch-all)
if os.path.exists("./frontend/dist"):
    app.mount("/assets", StaticFiles(directory="./frontend/dist/assets"), name="assets")
    
    @app.get("/")
    async def serve_spa():
        return FileResponse('./frontend/dist/index.html')
    
    @app.get("/{path:path}")
    async def serve_spa_fallback(path: str):
        # Don't serve SPA for API routes
        if path.startswith("api/") or path == "ws":
            raise HTTPException(status_code=404)
        # Check if file exists
        file_path = f"./frontend/dist/{path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html for client-side routing
        return FileResponse('./frontend/dist/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )