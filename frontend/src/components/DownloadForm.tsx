import React, { useState, useEffect } from 'react';
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
  Collapse,
  IconButton,
  Slider,
  Tooltip,
  Divider,
  Chip,
} from '@mui/material';
import Download from '@mui/icons-material/Download';
import Info from '@mui/icons-material/Info';
import ExpandMore from '@mui/icons-material/ExpandMore';
import ExpandLess from '@mui/icons-material/ExpandLess';
import Settings from '@mui/icons-material/Settings';
import Schedule from '@mui/icons-material/Schedule';
import Subtitles from '@mui/icons-material/Subtitles';
import Speed from '@mui/icons-material/Speed';
import Refresh from '@mui/icons-material/Refresh';
import BookmarkAdd from '@mui/icons-material/BookmarkAdd';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { downloadAPI } from '../api';
import { VideoInfo, DownloadPreset } from '../types';
import { useDownloadStore } from '../store/downloadStore';
import { useSettingsStore, showNotification } from '../store/settingsStore';

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

  // New feature states
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [subtitles, setSubtitles] = useState(false);
  const [subtitleLang, setSubtitleLang] = useState('en');
  const [speedLimit, setSpeedLimit] = useState(0); // 0 = unlimited
  const [autoRetry, setAutoRetry] = useState(true);
  const [maxRetries, setMaxRetries] = useState(3);
  const [scheduleDownload, setScheduleDownload] = useState(false);
  const [scheduledTime, setScheduledTime] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<string>('');

  const addDownload = useDownloadStore((state) => state.addDownload);
  const { presets, addPreset, notificationsEnabled } = useSettingsStore();

  // Apply preset when selected
  useEffect(() => {
    if (selectedPreset) {
      const preset = presets.find(p => p.id === selectedPreset);
      if (preset) {
        setQuality(preset.quality);
        setAudioOnly(preset.audio_only);
        if (preset.audio_format) setAudioFormat(preset.audio_format);
        setSubtitles(preset.subtitles);
        setSubtitleLang(preset.subtitle_lang);
        setSpeedLimit(preset.speed_limit);
        setAutoRetry(preset.auto_retry);
        setMaxRetries(preset.max_retries);
      }
    }
  }, [selectedPreset, presets]);

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

  const handleSaveAsPreset = () => {
    const presetName = prompt(t('presets.enterName') || 'Enter preset name:');
    if (!presetName) return;

    const newPreset: DownloadPreset = {
      id: `preset-${Date.now()}`,
      name: presetName,
      quality: audioOnly ? 'bestaudio' : quality,
      audio_only: audioOnly,
      audio_format: audioOnly ? audioFormat : undefined,
      subtitles,
      subtitle_lang: subtitleLang,
      speed_limit: speedLimit,
      auto_retry: autoRetry,
      max_retries: maxRetries,
    };

    addPreset(newPreset);
    toast.success(t('presets.saved') || 'Preset saved!');
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
        subtitles,
        subtitle_lang: subtitleLang,
        speed_limit: speedLimit > 0 ? speedLimit : undefined,
        scheduled_time: scheduleDownload && scheduledTime ? scheduledTime : undefined,
        auto_retry: autoRetry,
        max_retries: autoRetry ? maxRetries : undefined,
      });

      const download = await downloadAPI.get(response.download_id);
      addDownload(download);

      if (notificationsEnabled) {
        showNotification(
          t('notifications.downloadStarted'),
          videoInfo?.title || url
        );
      }

      toast.success(t('notifications.downloadStarted'));
      setUrl('');
      setVideoInfo(null);
    } catch (error) {
      toast.error(t('notifications.downloadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const formatSpeedLimit = (value: number) => {
    if (value === 0) return t('settings.unlimited') || 'Unlimited';
    if (value >= 1024) return `${(value / 1024).toFixed(1)} MB/s`;
    return `${value} KB/s`;
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

        {/* Preset Selection */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>{t('presets.select') || 'Preset'}</InputLabel>
            <Select
              value={selectedPreset}
              onChange={(e) => setSelectedPreset(e.target.value)}
              label={t('presets.select') || 'Preset'}
              disabled={loading}
            >
              <MenuItem value="">{t('presets.custom') || 'Custom'}</MenuItem>
              {presets.map((preset) => (
                <MenuItem key={preset.id} value={preset.id}>
                  {preset.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip title={t('presets.saveAsCurrent') || 'Save current settings as preset'}>
            <IconButton onClick={handleSaveAsPreset} color="primary">
              <BookmarkAdd />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Basic Options */}
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
            label={t('download.playlist') || 'Download Playlist'}
          />

          {!audioOnly && (
            <FormControl sx={{ minWidth: 180 }}>
              <InputLabel>{t('download.quality') || 'Quality'}</InputLabel>
              <Select
                value={quality}
                onChange={(e) => setQuality(e.target.value)}
                label={t('download.quality') || 'Quality'}
                disabled={loading}
              >
                <MenuItem value="best">{t('quality.best') || 'Best Available'}</MenuItem>
                <MenuItem value="bestvideo[height<=2160]+bestaudio/best">4K (2160p)</MenuItem>
                <MenuItem value="bestvideo[height<=1440]+bestaudio/best">1440p (2K)</MenuItem>
                <MenuItem value="bestvideo[height<=1080]+bestaudio/best">1080p (Full HD)</MenuItem>
                <MenuItem value="bestvideo[height<=720]+bestaudio/best">720p (HD)</MenuItem>
                <MenuItem value="bestvideo[height<=480]+bestaudio/best">480p</MenuItem>
                <MenuItem value="bestvideo[height<=360]+bestaudio/best">360p</MenuItem>
                <MenuItem value="worst">{t('quality.lowest') || 'Lowest Quality'}</MenuItem>
              </Select>
            </FormControl>
          )}
        </Box>

        {/* Advanced Options Toggle */}
        <Button
          variant="text"
          onClick={() => setShowAdvanced(!showAdvanced)}
          startIcon={<Settings />}
          endIcon={showAdvanced ? <ExpandLess /> : <ExpandMore />}
          sx={{ mb: 1 }}
        >
          {t('settings.advanced') || 'Advanced Options'}
        </Button>

        <Collapse in={showAdvanced}>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            {/* Subtitles */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={subtitles}
                    onChange={(e) => setSubtitles(e.target.checked)}
                    disabled={loading}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Subtitles fontSize="small" />
                    {t('settings.subtitles') || 'Download Subtitles'}
                  </Box>
                }
              />
              {subtitles && (
                <FormControl sx={{ minWidth: 120 }}>
                  <InputLabel>{t('settings.subtitleLang') || 'Language'}</InputLabel>
                  <Select
                    value={subtitleLang}
                    onChange={(e) => setSubtitleLang(e.target.value)}
                    label={t('settings.subtitleLang') || 'Language'}
                    disabled={loading}
                    size="small"
                  >
                    <MenuItem value="en">English</MenuItem>
                    <MenuItem value="de">Deutsch</MenuItem>
                    <MenuItem value="es">Español</MenuItem>
                    <MenuItem value="fr">Français</MenuItem>
                    <MenuItem value="it">Italiano</MenuItem>
                    <MenuItem value="pt">Português</MenuItem>
                    <MenuItem value="ru">Русский</MenuItem>
                    <MenuItem value="ja">日本語</MenuItem>
                    <MenuItem value="ko">한국어</MenuItem>
                    <MenuItem value="zh">中文</MenuItem>
                    <MenuItem value="all">{t('settings.allLangs') || 'All Available'}</MenuItem>
                  </Select>
                </FormControl>
              )}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Speed Limit */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                <Speed fontSize="small" />
                {t('settings.speedLimit') || 'Speed Limit'}: {formatSpeedLimit(speedLimit)}
              </Typography>
              <Slider
                value={speedLimit}
                onChange={(_, value) => setSpeedLimit(value as number)}
                min={0}
                max={10240}
                step={256}
                marks={[
                  { value: 0, label: t('settings.unlimited') || 'Unlimited' },
                  { value: 2560, label: '2.5 MB/s' },
                  { value: 5120, label: '5 MB/s' },
                  { value: 10240, label: '10 MB/s' },
                ]}
                disabled={loading}
              />
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Auto Retry */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoRetry}
                    onChange={(e) => setAutoRetry(e.target.checked)}
                    disabled={loading}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Refresh fontSize="small" />
                    {t('settings.autoRetry') || 'Auto-Retry on Failure'}
                  </Box>
                }
              />
              {autoRetry && (
                <FormControl sx={{ minWidth: 100 }}>
                  <InputLabel>{t('settings.maxRetries') || 'Max Retries'}</InputLabel>
                  <Select
                    value={maxRetries}
                    onChange={(e) => setMaxRetries(Number(e.target.value))}
                    label={t('settings.maxRetries') || 'Max Retries'}
                    disabled={loading}
                    size="small"
                  >
                    <MenuItem value={1}>1</MenuItem>
                    <MenuItem value={2}>2</MenuItem>
                    <MenuItem value={3}>3</MenuItem>
                    <MenuItem value={5}>5</MenuItem>
                    <MenuItem value={10}>10</MenuItem>
                  </Select>
                </FormControl>
              )}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Schedule Download */}
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={scheduleDownload}
                    onChange={(e) => setScheduleDownload(e.target.checked)}
                    disabled={loading}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Schedule fontSize="small" />
                    {t('settings.scheduleDownload') || 'Schedule Download'}
                  </Box>
                }
              />
              {scheduleDownload && (
                <TextField
                  type="datetime-local"
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  disabled={loading}
                  size="small"
                  InputLabelProps={{ shrink: true }}
                />
              )}
            </Box>
          </Paper>
        </Collapse>

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <Download />}
          size="large"
        >
          {loading ? t('download.downloading') : t('download.downloadButton')}
        </Button>
      </Box>
    </Paper>
  );
};
