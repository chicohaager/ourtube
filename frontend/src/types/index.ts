export interface DownloadRequest {
  url: string;
  quality?: string;
  audio_only?: boolean;
  playlist?: boolean;
  output_dir?: string;
  audio_format?: 'mp3' | 'flac' | 'ogg' | 'm4a' | 'wav' | 'aac' | 'opus';
  // New features
  subtitles?: boolean;
  subtitle_lang?: string;
  speed_limit?: number; // in KB/s, 0 = unlimited
  scheduled_time?: string; // ISO datetime string
  auto_retry?: boolean;
  max_retries?: number;
}

export interface DownloadStatus {
  id: string;
  url: string;
  status: 'queued' | 'downloading' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'scheduled' | 'retrying';
  progress?: number;
  filename?: string;
  error?: string;
  speed?: string;
  eta?: string;
  created_at: string;
  completed_at?: string;
  // New features
  scheduled_time?: string;
  retry_count?: number;
  max_retries?: number;
}

export interface VideoInfo {
  title: string;
  duration: number;
  thumbnail: string;
  uploader: string;
}


export interface WebSocketMessage {
  type: 'progress' | 'status' | 'completed' | 'error';
  download_id: string;
  progress?: number;
  status?: string;
  filename?: string;
  error?: string;
  speed?: string;
  eta?: string;
}

export interface FfmpegDownloadInfo {
  url: string;
  instructions: string;
  package_manager: string | null;
}

export interface YtdlpDownloadInfo {
  url: string;
  instructions: string;
  package_manager: string | null;
}

export interface ServerConfig {
  ffmpeg_available: boolean;
  ffmpeg_version: string;
  ffmpeg_updates_available: boolean;
  ffmpeg_download_info?: FfmpegDownloadInfo;
  max_concurrent_downloads: number;
  active_downloads: number;
  ytdl_auto_update: boolean;
  ytdlp_updates_available: boolean;
  ytdlp_available?: boolean;
  ytdlp_download_info?: YtdlpDownloadInfo;
  proxy: boolean;
  download_dir: string;
  output_template: string;
  supported_sites: string;
  ytdlp_version: string;
  platform: string;
}

export interface DirectoryItem {
  name: string;
  path: string;
  isDirectory: boolean;
  isParent?: boolean;
  isRoot?: boolean;
}

export interface DirectoryBrowseResponse {
  directories: DirectoryItem[];
  currentPath: string;
}

// Download preset/template for favorites
export interface DownloadPreset {
  id: string;
  name: string;
  quality: string;
  audio_only: boolean;
  audio_format?: string;
  subtitles: boolean;
  subtitle_lang: string;
  speed_limit: number;
  auto_retry: boolean;
  max_retries: number;
}

// App settings stored in localStorage
export interface AppSettings {
  darkMode: boolean;
  notificationsEnabled: boolean;
  defaultPreset?: string;
  maxConcurrentDownloads: number;
  presets: DownloadPreset[];
}