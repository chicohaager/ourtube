# OurTube Advanced Features

## Environment Variables

Configure OurTube behavior using these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_DIR` | `./downloads` | Directory where videos are saved |
| `OUTPUT_TEMPLATE` | `%(title)s.%(ext)s` | yt-dlp output filename template |
| `YTDL_UPDATE_INTERVAL` | `86400` | Seconds between yt-dlp auto-updates (24 hours) |
| `PROXY` | None | HTTP/HTTPS/SOCKS proxy URL |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Maximum simultaneous downloads |
| `YTDL_OPTIONS` | None | JSON string of additional yt-dlp options |
| `ENABLE_YTDL_UPDATE` | `true` | Enable automatic yt-dlp updates |
| `HISTORY_FILE` | `./download_history.json` | Path to download history file |
| `MAX_HISTORY_SIZE` | `1000` | Maximum number of downloads to keep in history |

## API Endpoints

### New Endpoints

- `GET /api/config` - Get server configuration and capabilities
- `POST /api/update-ytdlp` - Manually trigger yt-dlp update
- `GET /api/formats?url=URL` - Get available formats for a video

### Enhanced Download Options

The `/api/download` endpoint now accepts additional parameters:

```json
{
  "url": "https://youtube.com/watch?v=...",
  "format": "best",
  "audio_only": false,
  "playlist": false,
  "output_dir": "/custom/path",
  "quality": "1080",  // or "720", "480", etc.
  "custom_args": "{\"writesubtitles\": true}",  // JSON string
  "output_template": "%(uploader)s/%(title)s.%(ext)s",
  "proxy": "socks5://127.0.0.1:1080"
}
```

## Features

### 1. Automatic yt-dlp Updates
- yt-dlp is automatically updated every 24 hours (configurable)
- Manual updates via API endpoint
- Can be disabled with `ENABLE_YTDL_UPDATE=false`

### 2. Proxy Support
- Global proxy configuration via `PROXY` environment variable
- Per-download proxy override in API requests
- Supports HTTP, HTTPS, and SOCKS proxies

### 3. Download Queue Management
- Concurrent download limit (default: 3)
- Downloads queue automatically when limit reached
- Configure with `MAX_CONCURRENT_DOWNLOADS`

### 4. Custom yt-dlp Options
- Global options via `YTDL_OPTIONS` environment variable
- Per-download custom arguments
- Full yt-dlp feature support

### 5. Quality Selection
- Specify video quality (1080p, 720p, etc.)
- Automatic fallback to best available
- Works with or without ffmpeg

### 6. Download History
- Persistent download history across restarts
- Automatic history pruning (keeps latest 1000)
- Saved to JSON file

### 7. Custom Output Templates
- Configure global template via environment
- Per-download template override
- Full yt-dlp template syntax support

## Examples

### Running with Custom Configuration

```bash
PROXY=http://proxy.example.com:8080 \
MAX_CONCURRENT_DOWNLOADS=5 \
OUTPUT_TEMPLATE="%(upload_date)s - %(title)s.%(ext)s" \
python main.py
```

### Custom yt-dlp Options

Set global options:
```bash
export YTDL_OPTIONS='{"writesubtitles": true, "subtitleslangs": ["en", "de"]}'
```

### Download with Custom Arguments

```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=...",
    "quality": "720",
    "custom_args": "{\"writethumbnail\": true}",
    "output_template": "%(channel)s/%(title)s.%(ext)s"
  }'
```

## Differences from MeTube

While inspired by MeTube, OurTube includes:
- Modern React/TypeScript frontend with Material-UI
- Real-time WebSocket progress updates
- RESTful API design
- Configurable download queue limits
- Per-download proxy configuration
- Quality selection API
- Download history persistence
- Manual yt-dlp update trigger

## Notes

- ffmpeg is required for audio extraction and some video formats
- Download history is saved every minute and on shutdown
- All yt-dlp supported sites work (1000+ sites)
- Custom arguments must be valid JSON