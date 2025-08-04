import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Typography,
  CircularProgress,
} from '@mui/material';
import Download from '@mui/icons-material/Download';
import Info from '@mui/icons-material/Info';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { downloadAPI } from '../api';
import { VideoInfo } from '../types';
import { useDownloadStore } from '../store/downloadStore';

export const DownloadForm: React.FC = () => {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');
  const [audioOnly, setAudioOnly] = useState(false);
  const [playlist, setPlaylist] = useState(false);
  const [quality, setQuality] = useState('best');
  const [audioFormat, setAudioFormat] = useState('mp3');
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  
  const addDownload = useDownloadStore((state) => state.addDownload);

  const handleGetInfo = async () => {
    if (!url) {
      toast.error(t('download.urlPlaceholder'));
      return;
    }

    setLoadingInfo(true);
    try {
      const info = await downloadAPI.getVideoInfo(url);
      setVideoInfo(info);
      toast.success(t('notifications.videoInfoRetrieved'));
    } catch (error) {
      toast.error(t('notifications.videoInfoFailed'));
    } finally {
      setLoadingInfo(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url) {
      toast.error(t('download.urlPlaceholder'));
      return;
    }

    setLoading(true);
    try {
      const response = await downloadAPI.create({
        url,
        audio_only: audioOnly,
        playlist,
        quality: audioOnly ? 'bestaudio' : quality,
        audio_format: audioOnly ? audioFormat as 'mp3' | 'flac' | 'ogg' | 'm4a' | 'wav' | 'aac' | 'opus' : undefined,
      });

      const download = await downloadAPI.get(response.download_id);
      addDownload(download);
      
      toast.success(t('notifications.downloadStarted'));
      setUrl('');
      setVideoInfo(null);
    } catch (error) {
      toast.error(t('notifications.downloadFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        {t('download.title')}
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit}>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            label="Video URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={t('download.urlPlaceholder')}
            disabled={loading}
          />
          <Button
            variant="outlined"
            onClick={handleGetInfo}
            disabled={loading || loadingInfo}
            startIcon={loadingInfo ? <CircularProgress size={20} /> : <Info />}
          >
            Info
          </Button>
        </Box>

        {videoInfo && (
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              {videoInfo.thumbnail && (
                <Box 
                  sx={{ 
                    flexShrink: 0,
                    width: 200,
                    height: 150,
                    borderRadius: 1,
                    overflow: 'hidden',
                    backgroundColor: 'grey.300'
                  }}
                >
                  <img 
                    src={`/api/thumbnail?url=${encodeURIComponent(videoInfo.thumbnail)}`} 
                    alt="Video thumbnail"
                    style={{ 
                      width: '100%', 
                      height: '100%', 
                      objectFit: 'cover' 
                    }}
                    onError={(e) => {
                      const img = e.target as HTMLImageElement;
                      // Try direct URL as fallback
                      if (!img.src.includes(videoInfo.thumbnail)) {
                        img.src = videoInfo.thumbnail;
                      } else {
                        img.style.display = 'none';
                      }
                    }}
                  />
                </Box>
              )}
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" gutterBottom>
                  {videoInfo.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('videoInfo.uploader')}: {videoInfo.uploader}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('videoInfo.duration')}: {Math.floor(videoInfo.duration / 60)}:{(videoInfo.duration % 60).toString().padStart(2, '0')}
                </Typography>
              </Box>
            </Box>
          </Paper>
        )}


        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
          <FormControlLabel
            control={
              <Switch
                checked={audioOnly}
                onChange={(e) => setAudioOnly(e.target.checked)}
                disabled={loading}
              />
            }
            label={t('download.audioOnly')}
          />

          {audioOnly && (
            <FormControl sx={{ minWidth: 120 }}>
              <InputLabel>{t('download.audioFormat')}</InputLabel>
              <Select
                value={audioFormat}
                onChange={(e) => setAudioFormat(e.target.value)}
                label={t('download.audioFormat')}
                disabled={loading}
              >
                <MenuItem value="mp3">MP3</MenuItem>
                <MenuItem value="flac">FLAC</MenuItem>
                <MenuItem value="ogg">OGG</MenuItem>
                <MenuItem value="m4a">M4A</MenuItem>
                <MenuItem value="wav">WAV</MenuItem>
                <MenuItem value="aac">AAC</MenuItem>
                <MenuItem value="opus">OPUS</MenuItem>
              </Select>
            </FormControl>
          )}
          
          <FormControlLabel
            control={
              <Switch
                checked={playlist}
                onChange={(e) => setPlaylist(e.target.checked)}
                disabled={loading}
              />
            }
            label="Download Playlist"
          />

          {!audioOnly && (
            <FormControl sx={{ minWidth: 180 }}>
              <InputLabel>Quality</InputLabel>
              <Select
                value={quality}
                onChange={(e) => setQuality(e.target.value)}
                label="Quality"
                disabled={loading}
              >
                <MenuItem value="best">Best Available</MenuItem>
                <MenuItem value="bestvideo[height<=2160]+bestaudio/best">4K (2160p)</MenuItem>
                <MenuItem value="bestvideo[height<=1440]+bestaudio/best">1440p (2K)</MenuItem>
                <MenuItem value="bestvideo[height<=1080]+bestaudio/best">1080p (Full HD)</MenuItem>
                <MenuItem value="bestvideo[height<=720]+bestaudio/best">720p (HD)</MenuItem>
                <MenuItem value="bestvideo[height<=480]+bestaudio/best">480p (Standard)</MenuItem>
                <MenuItem value="bestvideo[height<=360]+bestaudio/best">360p (Mobile)</MenuItem>
                <MenuItem value="worst">Lowest Quality</MenuItem>
              </Select>
            </FormControl>
          )}
        </Box>

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <Download />}
        >
          {loading ? t('download.downloading') : t('download.downloadButton')}
        </Button>
      </Box>
    </Paper>
  );
};