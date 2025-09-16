# OurTube - Modern Video & Audio Downloader

[![Docker Pulls](https://img.shields.io/docker/pulls/chicohaager/ourtube)](https://hub.docker.com/r/chicohaager/ourtube)
[![Docker Stars](https://img.shields.io/docker/stars/chicohaager/ourtube)](https://hub.docker.com/r/chicohaager/ourtube)
[![Image Size](https://img.shields.io/docker/image-size/chicohaager/ourtube/latest)](https://hub.docker.com/r/chicohaager/ourtube)

A modern, full-stack web application for downloading videos and audio from YouTube and 1000+ other platforms.

## ✨ Features

- 🎥 **Multi-platform support**: YouTube and 1000+ video sites via yt-dlp
- 🎵 **Audio formats**: MP3, FLAC, OGG, M4A, WAV, AAC, OPUS
- 📊 **Real-time progress**: Live progress bars with speed/ETA
- 🌍 **Multilingual**: German/English with easy switching
- 🎨 **Modern UI**: Material-UI with dark/light mode
- 🖼️ **Video preview**: Thumbnail and info before download
- ⚡ **Fast**: Optimized API with caching (0.04s cached requests)

## 🚀 Quick Start

### Simple Run
```bash
docker run -d \
  --name ourtube \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  chicohaager/ourtube:latest
```

### With Docker Compose
```yaml
version: '3.8'
services:
  ourtube:
    image: chicohaager/ourtube:latest
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/app/downloads
      - ./config:/app/config
    environment:
      - MAX_CONCURRENT_DOWNLOADS=3
      - ENABLE_YTDL_UPDATE=true
    restart: unless-stopped
```

## 📋 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_DIR` | `/app/downloads` | Download directory |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Max simultaneous downloads |
| `ENABLE_YTDL_UPDATE` | `true` | Auto-update yt-dlp |
| `YTDL_UPDATE_INTERVAL` | `86400` | Update interval (seconds) |
| `OUTPUT_TEMPLATE` | `%(title)s.%(ext)s` | Filename template |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

## 🔧 Advanced Usage

### With Custom Configuration
```bash
docker run -d \
  --name ourtube \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  -e MAX_CONCURRENT_DOWNLOADS=5 \
  -e ENABLE_YTDL_UPDATE=true \
  chicohaager/ourtube:latest
```

### With Proxy Support
```bash
docker run -d \
  --name ourtube \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  -e PROXY=http://proxy.example.com:8080 \
  chicohaager/ourtube:latest
```

## 📁 Volume Mounts

- `/app/downloads` - Downloaded files
- `/app/config` - Configuration files (optional)

## 🌐 Access

After starting the container, access the web interface at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🛠️ Supported Platforms

- YouTube, Vimeo, Twitch, TikTok, Instagram
- SoundCloud, Bandcamp, many more
- 1000+ platforms via yt-dlp

## 📊 Tags

- `latest` - Latest stable release
- `v1.0.0` - Specific version
- `stable` - Stable release branch

## 🔗 Links

- **GitHub**: https://github.com/chicohaager/ourtube
- **Documentation**: https://github.com/chicohaager/ourtube#readme
- **Issues**: https://github.com/chicohaager/ourtube/issues

## 📄 License

MIT License - see [LICENSE](https://github.com/chicohaager/ourtube/blob/main/LICENSE)