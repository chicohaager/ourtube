export interface DownloadRequest {
  url: string;
  quality?: string;
  audio_only?: boolean;
  playlist?: boolean;
  output_dir?: string;
  audio_format?: 'mp3' | 'flac' | 'ogg' | 'm4a' | 'wav' | 'aac' | 'opus';
}

export interface DownloadStatus {
  id: string;
  url: string;
  status: 'queued' | 'downloading' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  filename?: string;
  error?: string;
  speed?: string;
  eta?: string;
  created_at: string;
  completed_at?: string;
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

export interface ServerConfig {
  ffmpeg_available: boolean;
  ffmpeg_version: string;
  ffmpeg_updates_available: boolean;
  ffmpeg_download_info?: FfmpegDownloadInfo;
  max_concurrent_downloads: number;
  active_downloads: number;
  ytdl_auto_update: boolean;
  ytdlp_updates_available: boolean;
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