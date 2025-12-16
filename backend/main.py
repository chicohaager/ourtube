from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List
import yt_dlp
import asyncio
import os
import uuid
from datetime import datetime
import json
import subprocess
import logging
from contextlib import asynccontextmanager
import sys
import re
try:
    from backend.security_config import setup_security
except ImportError:
    from security_config import setup_security

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
# Use script directory as base for relative paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CONFIG = os.path.join(_SCRIPT_DIR, "config", "settings.json")
_DEFAULT_DOWNLOADS = os.path.join(_SCRIPT_DIR, "downloads")

CONFIG_FILE = os.path.abspath(os.getenv("CONFIG_FILE", _DEFAULT_CONFIG))
DOWNLOAD_DIR = os.path.abspath(os.getenv("DOWNLOAD_DIR", _DEFAULT_DOWNLOADS))
OUTPUT_TEMPLATE = os.getenv("OUTPUT_TEMPLATE", "%(title)s.%(ext)s")
YTDL_UPDATE_INTERVAL = int(os.getenv("YTDL_UPDATE_INTERVAL", "86400"))  # 24 hours
PROXY = os.getenv("PROXY", None)
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
YTDL_OPTIONS = os.getenv("YTDL_OPTIONS", None)
ENABLE_YTDL_UPDATE = os.getenv("ENABLE_YTDL_UPDATE", "true").lower() == "true"
HISTORY_FILE = os.path.abspath(os.getenv("HISTORY_FILE", os.path.join(_SCRIPT_DIR, "download_history.json")))
MAX_HISTORY_SIZE = int(os.getenv("MAX_HISTORY_SIZE", "1000"))

def load_config():
    """Load configuration from config file"""
    global DOWNLOAD_DIR
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                if 'download_dir' in config:
                    DOWNLOAD_DIR = os.path.abspath(config['download_dir'])
                    logger.info(f"Loaded download_dir from config: {DOWNLOAD_DIR}")
    except Exception as e:
        logger.warning(f"Could not load config file: {e}")

def save_config():
    """Save configuration to config file"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        config = {
            'download_dir': DOWNLOAD_DIR
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved config to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Could not save config file: {e}")

# Global variable to track active downloads
active_downloads = 0
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename to be safe for all operating systems.

    Always uses Windows-compatible rules since files may be accessed
    via network shares or volume mounts from Windows clients.
    """
    # Remove or replace invalid characters
    # Always use Windows rules for maximum compatibility
    # Windows reserved characters: < > : " / \ | ? *
    invalid_chars = r'[<>:"|?*\/\\\x00-\x1f]'
    filename = re.sub(invalid_chars, '_', filename)

    # Remove leading/trailing dots and spaces (Windows doesn't like these)
    filename = filename.strip('. ')

    # Always check Windows reserved names for compatibility
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    name_without_ext = filename.split('.')[0].upper()
    if name_without_ext in reserved_names:
        filename = f"_{filename}"

    # Truncate if too long (accounting for file extension)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        if ext:
            max_name_length = max_length - len(ext)
            filename = name[:max_name_length] + ext
        else:
            filename = filename[:max_length]

    # Fallback if filename is empty after sanitization
    if not filename:
        filename = "download"

    return filename

# Simple in-memory cache for video info with size limit
video_info_cache = {}
cache_max_age = 3600  # 1 hour
cache_max_size = 100  # Maximum number of cached entries

def cleanup_video_cache():
    """Remove expired entries from cache and limit size"""
    global video_info_cache
    now = datetime.now().timestamp()

    # Remove expired entries
    expired_keys = [
        key for key, (_, timestamp) in video_info_cache.items()
        if now - timestamp >= cache_max_age
    ]
    for key in expired_keys:
        del video_info_cache[key]

    # If still too large, remove oldest entries
    if len(video_info_cache) > cache_max_size:
        sorted_items = sorted(video_info_cache.items(), key=lambda x: x[1][1])
        items_to_remove = len(video_info_cache) - cache_max_size
        for key, _ in sorted_items[:items_to_remove]:
            del video_info_cache[key]

async def update_ytdlp():
    """Update yt-dlp to the latest version"""
    if not ENABLE_YTDL_UPDATE:
        return

    try:
        logger.info("Checking for yt-dlp updates...")
        # Try to find the correct Python executable
        python_exec = sys.executable if hasattr(sys, 'executable') else 'python3'
        result = subprocess.run(
            [python_exec, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout for pip install
        )
        if "Successfully installed" in result.stdout:
            logger.info("yt-dlp updated successfully")
        else:
            logger.info("yt-dlp is already up to date")
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp update timed out")
    except Exception as e:
        logger.error(f"Failed to update yt-dlp: {e}")

async def periodic_ytdlp_update():
    """Periodically update yt-dlp"""
    while True:
        await update_ytdlp()
        await asyncio.sleep(YTDL_UPDATE_INTERVAL)

async def check_ffmpeg_on_startup():
    """Check ffmpeg availability on startup"""
    global FFMPEG_AVAILABLE
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=10)
        FFMPEG_AVAILABLE = True
        logger.info(f"ffmpeg is available. Version: {get_ffmpeg_version()}")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        FFMPEG_AVAILABLE = False
        logger.warning("ffmpeg not found. Some video formats may not be downloadable.")
        logger.warning("Audio-only downloads (MP3) will not work without ffmpeg.")

async def periodic_history_save():
    """Periodically save download history"""
    while True:
        await asyncio.sleep(60)  # Save every minute
        save_download_history()

async def periodic_cache_cleanup():
    """Periodically clean up video info cache"""
    while True:
        await asyncio.sleep(300)  # Clean up every 5 minutes
        cleanup_video_cache()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Load saved config (download_dir, etc.)
    load_config()
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Check ffmpeg availability
    await check_ffmpeg_on_startup()
    
    # Load download history
    load_download_history()
    
    # Start periodic yt-dlp updates
    if ENABLE_YTDL_UPDATE:
        asyncio.create_task(periodic_ytdlp_update())
    
    # Start periodic history saves
    asyncio.create_task(periodic_history_save())

    # Start periodic cache cleanup
    asyncio.create_task(periodic_cache_cleanup())

    yield
    
    # Shutdown
    logger.info("Shutting down...")
    save_download_history()  # Final save

app = FastAPI(title="OurTube", version="1.0.0", lifespan=lifespan)

# ffmpeg availability is checked async on startup via lifespan
FFMPEG_AVAILABLE = False

# Setup security middleware (rate limiting, security headers, CORS)
setup_security(app)

class DownloadRequest(BaseModel):
    url: HttpUrl
    format: Optional[str] = "best"
    audio_only: Optional[bool] = False
    playlist: Optional[bool] = False
    output_dir: Optional[str] = None
    quality: Optional[str] = None  # e.g., "1080", "720", "480"
    audio_format: Optional[str] = "mp3"  # Audio format: mp3, flac, ogg, m4a, wav, aac, opus
    custom_args: Optional[str] = None  # Custom yt-dlp arguments
    output_template: Optional[str] = None  # Custom filename template
    proxy: Optional[str] = None  # Override global proxy
    video_format_id: Optional[str] = None  # Specific video format
    audio_format_id: Optional[str] = None  # Specific audio format
    # New features
    subtitles: Optional[bool] = False  # Download subtitles
    subtitle_lang: Optional[str] = "en"  # Subtitle language
    speed_limit: Optional[int] = None  # Speed limit in KB/s
    scheduled_time: Optional[str] = None  # ISO datetime for scheduling
    auto_retry: Optional[bool] = True  # Auto-retry on failure
    max_retries: Optional[int] = 3  # Maximum retry attempts

class DownloadStatus(BaseModel):
    id: str
    url: str
    status: str  # queued, downloading, processing, completed, failed, cancelled, scheduled, retrying
    progress: Optional[float] = 0
    filename: Optional[str] = None
    error: Optional[str] = None
    speed: Optional[str] = None
    eta: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    # New features
    scheduled_time: Optional[datetime] = None
    retry_count: Optional[int] = 0
    max_retries: Optional[int] = 3

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients, removing dead connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to websocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
downloads: Dict[str, DownloadStatus] = {}

def load_download_history():
    """Load download history from file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history_data = json.load(f)
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

def save_download_history():
    """Save download history to file"""
    try:
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
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save download history: {e}")

class DownloadCancelled(Exception):
    """Exception raised when a download is cancelled"""
    pass

class DownloadProgress:
    def __init__(self, download_id: str, loop=None):
        self.download_id = download_id
        self.loop = loop

    def __call__(self, d):
        # Check if download was cancelled
        if self.download_id in downloads and downloads[self.download_id].status == 'cancelled':
            raise DownloadCancelled(f"Download {self.download_id} was cancelled by user")

        if d['status'] == 'downloading':
            # Handle fragmented downloads where total_bytes may be None or estimated
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)

            # Calculate progress safely, capped at 100%
            if total > 0 and downloaded >= 0:
                progress = min(100.0, (downloaded / total) * 100)
            else:
                # Fallback: use fragment info if available
                fragment_index = d.get('fragment_index', 0)
                fragment_count = d.get('fragment_count', 0)
                if fragment_count > 0:
                    progress = (fragment_index / fragment_count) * 100
                else:
                    progress = 0

            downloads[self.download_id].progress = progress
            
            # Extract speed and ETA from yt-dlp
            speed = d.get('_speed_str', d.get('speed'))
            eta = d.get('_eta_str', d.get('eta'))
            
            # Format speed if it's a number
            if isinstance(speed, (int, float)) and speed > 0:
                if speed > 1024 * 1024:
                    speed = f"{speed / (1024 * 1024):.1f}MB/s"
                elif speed > 1024:
                    speed = f"{speed / 1024:.1f}KB/s"
                else:
                    speed = f"{speed:.1f}B/s"
            elif not isinstance(speed, str):
                speed = None
                
            # Format ETA if it's a number (seconds)
            if isinstance(eta, (int, float)) and eta > 0:
                if eta > 3600:
                    hours = int(eta // 3600)
                    minutes = int((eta % 3600) // 60)
                    eta = f"{hours}h {minutes}m"
                elif eta > 60:
                    minutes = int(eta // 60)
                    seconds = int(eta % 60)
                    eta = f"{minutes}m {seconds}s"
                else:
                    eta = f"{int(eta)}s"
            elif not isinstance(eta, str):
                eta = None
            
            # Update download status
            downloads[self.download_id].speed = speed
            downloads[self.download_id].eta = eta
            
            # Schedule the broadcast in the main event loop
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({
                        "type": "progress",
                        "download_id": self.download_id,
                        "progress": progress,
                        "speed": speed,
                        "eta": eta
                    }), 
                    self.loop
                )
        elif d['status'] == 'finished':
            downloads[self.download_id].status = 'processing'
            filename = d.get('filename')
            if filename:
                # Sanitize the filename to prevent issues
                downloads[self.download_id].filename = sanitize_filename(os.path.basename(filename))

def get_ydl_opts(request: DownloadRequest, download_id: str, loop=None):
    # Use custom or default output directory
    output_dir = request.output_dir or DOWNLOAD_DIR
    
    # Ensure we're using absolute paths
    output_dir = os.path.abspath(output_dir)
    
    # Use custom or default output template
    template = request.output_template or OUTPUT_TEMPLATE
    output_template = os.path.join(output_dir, template)
    
    opts = {
        'outtmpl': output_template,
        'progress_hooks': [DownloadProgress(download_id, loop)],
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,  # Sanitize filenames for all platforms
        'windowsfilenames': True,   # Ensure Windows compatibility
    }
    
    # Add proxy if specified
    if request.proxy or PROXY:
        opts['proxy'] = request.proxy or PROXY
    
    # Handle specific format selection
    if request.video_format_id or request.audio_format_id:
        if request.video_format_id and request.audio_format_id:
            # Both video and audio specified
            opts['format'] = f'{request.video_format_id}+{request.audio_format_id}'
        elif request.video_format_id:
            # Only video specified
            opts['format'] = request.video_format_id
        elif request.audio_format_id:
            # Only audio specified
            opts['format'] = request.audio_format_id
    # Handle quality selection  
    elif request.quality and not request.audio_only:
        # Quality might be a format string from frontend like "bestvideo[height<=1080]+bestaudio/best"
        # or a simple quality like "1080", "720", etc.
        quality = request.quality
        
        # Check if it's a format string (contains brackets or +)
        if '[' in quality or '+' in quality:
            # It's already a format string from the frontend
            opts['format'] = quality
        else:
            # Convert simple quality number to format string
            quality_formats = {
                '4k': 'bestvideo[height<=2160]+bestaudio/best',
                '2160': 'bestvideo[height<=2160]+bestaudio/best',
                '1440': 'bestvideo[height<=1440]+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best',
                '720': 'bestvideo[height<=720]+bestaudio/best',
                '480': 'bestvideo[height<=480]+bestaudio/best',
                '360': 'bestvideo[height<=360]+bestaudio/best',
                '240': 'bestvideo[height<=240]+bestaudio/best',
                'best': 'best',
                'worst': 'worst'
            }
            opts['format'] = quality_formats.get(quality.lower(), 'best')
    elif request.audio_only:
        if not FFMPEG_AVAILABLE:
            raise Exception("Audio-only downloads require ffmpeg to be installed")
        
        # Get audio format and set quality
        audio_fmt = request.audio_format or 'mp3'
        
        # Map frontend formats to yt-dlp/ffmpeg codecs
        codec_map = {
            'mp3': 'mp3',
            'flac': 'flac',
            'ogg': 'vorbis',  # OGG uses vorbis codec
            'm4a': 'm4a', 
            'wav': 'wav',
            'aac': 'aac',
            'opus': 'opus'
        }
        
        # Set quality based on format
        quality_map = {
            'mp3': '192',
            'flac': '0',  # Lossless
            'vorbis': '192',  # OGG Vorbis
            'm4a': '192', 
            'wav': '0',   # Lossless
            'aac': '192',
            'opus': '128'
        }
        
        codec = codec_map.get(audio_fmt, 'mp3')
        
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': quality_map.get(codec, '192'),
            }],
        })
    else:
        # Handle format selection
        if request.format:
            # Check if format contains height filter which might cause issues
            if '[height' in request.format and not FFMPEG_AVAILABLE:
                # Height filters require ffmpeg for merging video+audio
                # Fallback to simpler format
                opts['format'] = 'best'
                logger.warning("Height filter requested but ffmpeg not available, using 'best' format")
            else:
                opts['format'] = request.format
        elif FFMPEG_AVAILABLE:
            opts['format'] = 'best'
        else:
            # Without ffmpeg, prefer single file formats that don't need merging
            opts['format'] = 'best[ext=mp4]/best[ext=webm]/best'
    
    if not request.playlist:
        opts['noplaylist'] = True
    
    # Apply custom YTDL_OPTIONS from environment
    if YTDL_OPTIONS:
        try:
            custom_opts = json.loads(YTDL_OPTIONS)
            opts.update(custom_opts)
        except json.JSONDecodeError:
            logger.error("Invalid YTDL_OPTIONS JSON")
    
    # Apply custom arguments from request
    if request.custom_args:
        try:
            # Parse custom args as JSON
            custom_args = json.loads(request.custom_args)
            opts.update(custom_args)
        except json.JSONDecodeError:
            logger.error("Invalid custom_args JSON")

    # Add subtitle support
    if request.subtitles:
        opts['writesubtitles'] = True
        opts['writeautomaticsub'] = True  # Also get auto-generated subs
        if request.subtitle_lang and request.subtitle_lang != 'all':
            opts['subtitleslangs'] = [request.subtitle_lang]
        else:
            opts['subtitleslangs'] = ['all']
        opts['subtitlesformat'] = 'srt/vtt/best'

    # Add speed limit support (convert KB/s to bytes/s)
    if request.speed_limit and request.speed_limit > 0:
        opts['ratelimit'] = request.speed_limit * 1024

    return opts

@app.post("/api/download")
async def create_download(request: DownloadRequest):
    download_id = str(uuid.uuid4())

    # Handle scheduled downloads
    scheduled_time = None
    initial_status = "queued"
    if request.scheduled_time:
        try:
            scheduled_time = datetime.fromisoformat(request.scheduled_time.replace('Z', '+00:00'))
            if scheduled_time > datetime.now(scheduled_time.tzinfo if scheduled_time.tzinfo else None):
                initial_status = "scheduled"
        except ValueError:
            logger.warning(f"Invalid scheduled_time format: {request.scheduled_time}")

    download_status = DownloadStatus(
        id=download_id,
        url=str(request.url),
        status=initial_status,
        created_at=datetime.now(),
        scheduled_time=scheduled_time,
        max_retries=request.max_retries or 3,
        retry_count=0
    )
    downloads[download_id] = download_status

    if initial_status == "scheduled":
        asyncio.create_task(schedule_download(download_id, request, scheduled_time))
    else:
        asyncio.create_task(process_download(download_id, request))

    return {"download_id": download_id, "status": initial_status}

async def schedule_download(download_id: str, request: DownloadRequest, scheduled_time: datetime):
    """Wait until scheduled time and then start the download"""
    now = datetime.now(scheduled_time.tzinfo if scheduled_time.tzinfo else None)
    wait_seconds = (scheduled_time - now).total_seconds()

    if wait_seconds > 0:
        logger.info(f"Download {download_id} scheduled for {scheduled_time}, waiting {wait_seconds:.0f} seconds")
        await asyncio.sleep(wait_seconds)

    # Check if download was cancelled while waiting
    if download_id in downloads and downloads[download_id].status == "scheduled":
        downloads[download_id].status = "queued"
        await manager.broadcast({
            "type": "status",
            "download_id": download_id,
            "status": "queued"
        })
        await process_download(download_id, request)

async def process_download(download_id: str, request: DownloadRequest):
    global active_downloads

    async with download_semaphore:  # Limit concurrent downloads
        try:
            active_downloads += 1

            # Check if already cancelled before starting
            if downloads[download_id].status == 'cancelled':
                logger.info(f"Download {download_id} was cancelled before starting")
                return

            downloads[download_id].status = "downloading"
            await manager.broadcast({
                "type": "status",
                "download_id": download_id,
                "status": "downloading"
            })

            loop = asyncio.get_event_loop()
            ydl_opts = get_ydl_opts(request, download_id, loop)

            await loop.run_in_executor(None, download_with_ydl, str(request.url), ydl_opts, download_id)

            # Check if cancelled during download
            if downloads[download_id].status == 'cancelled':
                logger.info(f"Download {download_id} was cancelled during processing")
                await manager.broadcast({
                    "type": "status",
                    "download_id": download_id,
                    "status": "cancelled"
                })
                return

            downloads[download_id].status = "completed"
            downloads[download_id].completed_at = datetime.now()
            downloads[download_id].progress = 100

            await manager.broadcast({
                "type": "completed",
                "download_id": download_id,
                "filename": downloads[download_id].filename
            })

            # Save history after successful download
            save_download_history()

        except DownloadCancelled:
            # Download was cancelled by user - this is expected behavior
            logger.info(f"Download {download_id} cancelled by user")
            downloads[download_id].status = "cancelled"
            await manager.broadcast({
                "type": "status",
                "download_id": download_id,
                "status": "cancelled"
            })
            save_download_history()

        except Exception as e:
            # Only mark as failed if not already cancelled
            if downloads[download_id].status != 'cancelled':
                # Check if we should auto-retry
                current_retry = downloads[download_id].retry_count or 0
                max_retries = downloads[download_id].max_retries or 0

                if request.auto_retry and current_retry < max_retries:
                    # Retry the download
                    downloads[download_id].retry_count = current_retry + 1
                    downloads[download_id].status = "retrying"
                    logger.info(f"Download {download_id} failed, retrying ({current_retry + 1}/{max_retries}): {e}")

                    await manager.broadcast({
                        "type": "status",
                        "download_id": download_id,
                        "status": "retrying",
                        "retry_count": current_retry + 1,
                        "max_retries": max_retries
                    })

                    # Wait a bit before retrying (don't decrement here - finally block handles it)
                    await asyncio.sleep(5)  # Wait 5 seconds before retry
                    asyncio.create_task(process_download(download_id, request))
                    return
                else:
                    downloads[download_id].status = "failed"
                    downloads[download_id].error = str(e)
                    await manager.broadcast({
                        "type": "error",
                        "download_id": download_id,
                        "error": str(e)
                    })

            # Save history after failed download too
            save_download_history()

        finally:
            active_downloads -= 1

def download_with_ydl(url: str, opts: dict, download_id: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

@app.get("/api/downloads")
async def get_downloads():
    return list(downloads.values())

@app.delete("/api/downloads")
async def clear_downloads():
    """Clear all download history"""
    global downloads
    downloads.clear()
    save_download_history()
    return {"message": "Download history cleared", "count": 0}

@app.get("/api/download/{download_id}")
async def get_download(download_id: str):
    if download_id not in downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    return downloads[download_id]

@app.delete("/api/download/{download_id}")
async def cancel_download(download_id: str):
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
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/api/info")
async def get_video_info(url: str):
    # Check cache first
    cache_key = url
    if cache_key in video_info_cache:
        cached_data, timestamp = video_info_cache[cache_key]
        if datetime.now().timestamp() - timestamp < cache_max_age:
            logger.info(f"Returning cached info for {url}")
            return cached_data

    try:
        # For YouTube URLs, extract video ID and use a much faster approach
        youtube_regex = r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
        match = re.search(youtube_regex, url)
        
        if match:
            # YouTube video detected - use super fast method
            video_id = match.group(1)
            
            # Quick API-less info fetch using yt-dlp's extract_info with minimal processing
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',  # Fast extraction
                'skip_download': True,
                'no_color': True,
                'socket_timeout': 10,
                'ignoreerrors': True,
            }
            
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )
            
            # Use predictable YouTube thumbnail URL
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            
            result = {
                "title": info.get('title', 'YouTube Video'),
                "duration": info.get('duration', 0),
                "thumbnail": thumbnail,
                "uploader": info.get('uploader', info.get('channel', 'Unknown')),
                "formats": []
            }
            
            # Cache the result
            video_info_cache[cache_key] = (result, datetime.now().timestamp())
            
            return result
        else:
            # Non-YouTube video - use standard but optimized approach
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'skip_download': True,
                'no_color': True,
                'socket_timeout': 10,
                'ignoreerrors': True,
            }
            
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )
            
            result = {
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail', ''),
                "uploader": info.get('uploader', 'Unknown'),
                "formats": []
            }
            
            # Cache the result
            video_info_cache[cache_key] = (result, datetime.now().timestamp())
            
            return result
            
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        logger.error(f"Video info error: {e}")
        # Return basic info even on error for YouTube
        if 'youtube' in url.lower() or 'youtu.be' in url.lower():
            try:
                video_id = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url).group(1)
                return {
                    "title": "YouTube Video",
                    "duration": 0,
                    "thumbnail": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                    "uploader": "Unknown",
                    "formats": []
                }
            except:
                pass
        raise HTTPException(status_code=400, detail=str(e))

def get_ytdlp_version():
    """Get current yt-dlp version"""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except:
        return "Not installed"

def get_ffmpeg_version():
    """Get current ffmpeg version"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extract version from first line (e.g., "ffmpeg version 4.4.2-0ubuntu0.22.04.1")
            first_line = result.stdout.split('\n')[0]
            version_parts = first_line.split(' ')
            if len(version_parts) >= 3:
                return version_parts[2]
            return "Unknown version"
        return "Unknown"
    except FileNotFoundError:
        return "Not installed"
    except subprocess.TimeoutExpired:
        return "Timeout checking version"
    except Exception as e:
        logger.error(f"Error getting ffmpeg version: {e}")
        return "Error checking version"

def get_ffmpeg_download_url():
    """Get platform-specific FFmpeg download URL and instructions"""
    system = sys.platform

    if system == 'win32':
        return {
            "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            "instructions": "Download the ZIP file, extract it, and add the 'bin' folder to your system PATH",
            "package_manager": None
        }
    elif system == 'darwin':  # macOS
        return {
            "url": "https://evermeet.cx/ffmpeg/ffmpeg-7.1.1.zip",
            "instructions": "Install via Homebrew: brew install ffmpeg",
            "package_manager": "brew install ffmpeg"
        }
    elif system == 'linux':
        # Try to detect the Linux distribution
        distro_info = {"instructions": "Install using your package manager", "package_manager": None}

        if os.path.exists('/etc/debian_version'):
            distro_info["package_manager"] = "sudo apt install ffmpeg"
        elif os.path.exists('/etc/redhat-release'):
            distro_info["package_manager"] = "sudo dnf install ffmpeg"
        elif os.path.exists('/etc/arch-release'):
            distro_info["package_manager"] = "sudo pacman -S ffmpeg"
        elif os.path.exists('/etc/SUSE-brand'):
            distro_info["package_manager"] = "sudo zypper install ffmpeg"

        distro_info["url"] = "https://ffmpeg.org/download.html#build-linux"
        return distro_info
    else:
        return {
            "url": "https://ffmpeg.org/download.html",
            "instructions": "Visit the FFmpeg download page for your platform",
            "package_manager": None
        }

def get_ytdlp_download_url():
    """Get platform-specific yt-dlp download URL and instructions"""
    system = sys.platform

    if system == 'win32':
        return {
            "url": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
            "instructions": "Download the executable and place it in your system PATH or the same directory as this application",
            "package_manager": "pip install yt-dlp"
        }
    elif system == 'darwin':  # macOS
        return {
            "url": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
            "instructions": "Install via Homebrew: brew install yt-dlp or use pip: pip install yt-dlp",
            "package_manager": "brew install yt-dlp"
        }
    elif system == 'linux':
        # Try to detect the Linux distribution
        distro_info = {"instructions": "Install using pip or your package manager", "package_manager": "pip install yt-dlp"}

        if os.path.exists('/etc/debian_version'):
            distro_info["package_manager"] = "sudo apt install yt-dlp"
        elif os.path.exists('/etc/redhat-release'):
            distro_info["package_manager"] = "pip install yt-dlp"
        elif os.path.exists('/etc/arch-release'):
            distro_info["package_manager"] = "sudo pacman -S yt-dlp"
        elif os.path.exists('/etc/SUSE-brand'):
            distro_info["package_manager"] = "pip install yt-dlp"

        distro_info["url"] = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        return distro_info
    else:
        return {
            "url": "https://github.com/yt-dlp/yt-dlp/releases/latest",
            "instructions": "Visit the yt-dlp releases page for your platform or install via pip: pip install yt-dlp",
            "package_manager": "pip install yt-dlp"
        }

async def check_ytdlp_updates():
    """Check if yt-dlp has updates available"""
    try:
        # Use pip to check for newer versions
        python_exec = sys.executable if hasattr(sys, 'executable') else 'python3'
        result = subprocess.run(
            [python_exec, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for pip list
        )
        if result.returncode == 0:
            outdated_packages = json.loads(result.stdout)
            for package in outdated_packages:
                if package.get('name') == 'yt-dlp':
                    return True
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Timeout checking yt-dlp updates")
        return False
    except Exception as e:
        logger.error(f"Error checking yt-dlp updates: {e}")
        return False

async def check_ffmpeg_updates():
    """Check if ffmpeg has updates available"""
    try:
        # Only check on Linux systems with apt
        if sys.platform != 'linux' or not os.path.exists('/usr/bin/apt'):
            return False

        # Check for updates (skip apt update which requires sudo)
        result = subprocess.run(
            ['apt', 'list', '--upgradable', 'ffmpeg'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if 'ffmpeg' in result.stdout and 'upgradable' in result.stdout:
            return True

        return False
    except subprocess.TimeoutExpired:
        logger.warning("Timeout checking ffmpeg updates")
        return False
    except Exception as e:
        logger.error(f"Error checking ffmpeg updates: {e}")
        return False

async def update_ffmpeg():
    """Update ffmpeg to the latest version"""
    try:
        system = sys.platform

        if system == 'linux':
            # Try to update using apt (Ubuntu/Debian)
            if os.path.exists('/usr/bin/apt'):
                logger.info("Updating ffmpeg using apt...")
                result = subprocess.run(
                    ['sudo', '-n', 'apt', 'install', '-y', 'ffmpeg'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout for apt install
                )
                if result.returncode == 0:
                    logger.info("ffmpeg updated successfully")
                    return {"success": True, "message": "ffmpeg updated successfully"}
                else:
                    return {"success": False, "message": "Failed to update ffmpeg. May require sudo privileges."}
            else:
                return {"success": False, "message": "Package manager not supported. Please update ffmpeg manually."}

        elif system == 'darwin':  # macOS
            # Try using homebrew
            if os.path.exists('/usr/local/bin/brew') or os.path.exists('/opt/homebrew/bin/brew'):
                logger.info("Updating ffmpeg using homebrew...")
                result = subprocess.run(
                    ['brew', 'upgrade', 'ffmpeg'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout for brew upgrade
                )
                if result.returncode == 0:
                    logger.info("ffmpeg updated successfully")
                    return {"success": True, "message": "ffmpeg updated successfully"}
                else:
                    return {"success": False, "message": "Failed to update ffmpeg via homebrew"}
            else:
                return {"success": False, "message": "Homebrew not found. Please install ffmpeg manually."}

        elif system == 'win32':
            return {"success": False, "message": "Windows auto-update not supported. Please download ffmpeg manually from ffmpeg.org"}

        else:
            return {"success": False, "message": f"Platform {system} not supported for auto-update"}

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg update timed out")
        return {"success": False, "message": "ffmpeg update timed out"}
    except Exception as e:
        logger.error(f"Failed to update ffmpeg: {e}")
        return {"success": False, "message": f"Error updating ffmpeg: {str(e)}"}

@app.get("/api/test")
async def test_endpoint():
    return {"message": "test works"}

@app.get("/api/config")
async def get_config():
    """Get current configuration and server capabilities"""
    ffmpeg_updates_available = await check_ffmpeg_updates() if FFMPEG_AVAILABLE else False
    ytdlp_updates_available = await check_ytdlp_updates()
    
    ytdlp_version = get_ytdlp_version()
    ytdlp_available = ytdlp_version != "Not installed"

    config = {
        "ffmpeg_available": FFMPEG_AVAILABLE,
        "ffmpeg_version": get_ffmpeg_version(),
        "ffmpeg_updates_available": ffmpeg_updates_available,
        "max_concurrent_downloads": MAX_CONCURRENT_DOWNLOADS,
        "active_downloads": active_downloads,
        "ytdl_auto_update": ENABLE_YTDL_UPDATE,
        "ytdlp_updates_available": ytdlp_updates_available,
        "ytdlp_available": ytdlp_available,
        "proxy": PROXY is not None,
        "download_dir": DOWNLOAD_DIR,
        "output_template": OUTPUT_TEMPLATE,
        "supported_sites": "YouTube and 1000+ other sites via yt-dlp",
        "ytdlp_version": ytdlp_version,
        "platform": sys.platform
    }

    # Add FFmpeg download info if not installed
    if not FFMPEG_AVAILABLE:
        config["ffmpeg_download_info"] = get_ffmpeg_download_url()

    # Add yt-dlp download info if not installed
    if not ytdlp_available:
        config["ytdlp_download_info"] = get_ytdlp_download_url()

    return config

@app.post("/api/update-ytdlp")
async def update_ytdlp_manual():
    """Manually trigger yt-dlp update"""
    await update_ytdlp()
    return {"message": "yt-dlp update triggered"}

@app.post("/api/update-ffmpeg")
async def update_ffmpeg_manual():
    """Manually trigger ffmpeg update"""
    result = await update_ffmpeg()
    if result["success"]:
        return {"message": result["message"], "new_version": get_ffmpeg_version()}
    else:
        raise HTTPException(status_code=500, detail=result["message"])

@app.post("/api/restart")
async def restart_application():
    """Restart the application to reload configuration"""
    logger.info("Restart requested - reloading FFmpeg status")
    
    # Instead of restarting the whole process, just reload FFmpeg status
    global FFMPEG_AVAILABLE
    await check_ffmpeg_on_startup()
    
    return {"message": "Application configuration reloaded", "ffmpeg_available": FFMPEG_AVAILABLE}

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

class DirectoryRequest(BaseModel):
    directory: str

@app.post("/api/set-download-dir")
async def set_download_directory(request: DirectoryRequest):
    """Set the download directory"""
    global DOWNLOAD_DIR
    try:
        # Convert to absolute path
        abs_dir = os.path.abspath(request.directory)
        # Validate directory exists or can be created
        os.makedirs(abs_dir, exist_ok=True)
        DOWNLOAD_DIR = abs_dir
        # Save to config file for persistence
        save_config()
        return {"message": "Download directory updated", "download_dir": DOWNLOAD_DIR}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid directory: {str(e)}")

@app.post("/api/open-download-dir")
async def open_download_directory():
    """Open the download directory in the system file manager"""
    try:
        # Ensure directory exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        # Use absolute path for all platforms
        abs_path = os.path.abspath(DOWNLOAD_DIR)

        # Check if we're in a GUI environment
        has_display = os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')

        if sys.platform == 'win32':
            # Windows: use os.startfile() for reliable folder opening
            try:
                os.startfile(abs_path)
                return {"message": "Download directory opened", "path": abs_path}
            except OSError as e:
                # Fallback to explorer.exe with proper path formatting
                try:
                    # Normalize path separators for Windows
                    win_path = abs_path.replace('/', '\\')
                    subprocess.run(['explorer.exe', win_path], check=False, capture_output=True)
                    return {"message": "Download directory opened", "path": abs_path}
                except Exception:
                    return {"message": f"Cannot open file manager on Windows. Directory: {abs_path}", "path": abs_path}
        elif sys.platform == 'darwin':  # macOS
            result = subprocess.run(['open', abs_path], check=False, capture_output=True, text=True)
            if result.returncode != 0:
                return {"message": f"Cannot open file manager on macOS. Directory: {abs_path}", "path": abs_path}
        else:  # Linux/Unix
            if not has_display:
                # No GUI available - common in Docker/server environments
                return {"message": f"File manager not available in headless environment. Directory: {abs_path}", "path": abs_path}

            # Try multiple methods for Linux with GUI
            opened = False
            for opener in ['xdg-open', 'gnome-open', 'kde-open', 'nautilus', 'thunar', 'pcmanfm', 'dolphin', 'nemo']:
                try:
                    result = subprocess.run([opener, abs_path], check=True, capture_output=True, text=True, timeout=5)
                    opened = True
                    break
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                    continue

            if not opened:
                return {"message": f"No suitable file manager found. Directory: {abs_path}", "path": abs_path}

        return {"message": "Download directory opened", "path": abs_path}
    except Exception as e:
        error_msg = f"Failed to open directory: {str(e)}"
        logger.error(error_msg)
        # Don't raise HTTP error, just return the path so user can still access it
        return {"message": f"Cannot open file manager: {str(e)}. Directory: {os.path.abspath(DOWNLOAD_DIR)}", "path": os.path.abspath(DOWNLOAD_DIR)}

@app.get("/api/browse-directories")
async def browse_directories(path: str = ""):
    """Browse directories for directory picker"""
    try:
        # Handle empty path or root indicators
        if not path or path in ['/', '\\', '.']:
            if sys.platform == 'win32':
                # Windows: Return list of available drives
                import string
                drives = []
                for drive in string.ascii_uppercase:
                    drive_path = f"{drive}:\\"
                    if os.path.exists(drive_path):
                        drives.append({
                            "name": f"{drive}:",
                            "path": drive_path,
                            "isDirectory": True,
                            "isRoot": True
                        })
                return {"directories": drives, "currentPath": ""}
            else:
                # Unix/Linux/Mac: Start at root
                path = "/"

        # Security: Normalize and validate path
        path = os.path.normpath(path)

        # Handle Windows drive letters (e.g., "C:" without backslash)
        if sys.platform == 'win32' and len(path) == 2 and path[1] == ':':
            path = path + '\\'

        # Check if path exists and is accessible
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")

        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="Path is not a directory")

        directories = []

        # Add parent directory option (except for root)
        parent_path = os.path.dirname(path)
        is_root = (
            path == '/' or
            (sys.platform == 'win32' and len(path) <= 3 and path[1:2] == ':')
        )

        if not is_root and parent_path and parent_path != path:
            directories.append({
                "name": "..",
                "path": parent_path,
                "isDirectory": True,
                "isParent": True
            })
        elif sys.platform == 'win32' and is_root:
            # On Windows root drive, add option to go back to drive list
            directories.append({
                "name": "..",
                "path": "",
                "isDirectory": True,
                "isParent": True
            })

        # List directories only
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isdir(item_path):
                        # Skip hidden directories (starting with .)
                        if not item.startswith('.'):
                            directories.append({
                                "name": item,
                                "path": item_path,
                                "isDirectory": True
                            })
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    continue
        except PermissionError:
            # If we can't read the directory, return what we have
            pass

        return {
            "directories": directories,
            "currentPath": path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Directory browse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to browse directory: {str(e)}")

@app.get("/api/thumbnail")
async def get_thumbnail_proxy(url: str):
    """Proxy thumbnail images to avoid CORS issues"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                return Response(content=response.content, media_type=content_type)
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch thumbnail")
    except Exception as e:
        logger.error(f"Thumbnail proxy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch thumbnail")

# Frontend serving routes (must be last due to catch-all)
if os.path.exists("./frontend/dist"):
    app.mount("/assets", StaticFiles(directory="./frontend/dist/assets"), name="assets")
    
    @app.get("/logo.png")
    async def serve_logo():
        return FileResponse('./frontend/dist/logo.png')
    
    @app.get("/")
    async def serve_spa():
        return FileResponse('./frontend/dist/index.html')
    
    @app.get("/{path:path}")
    async def serve_spa_fallback(path: str):
        if path.startswith("api/") or path == "ws":
            raise HTTPException(status_code=404)
        return FileResponse('./frontend/dist/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)