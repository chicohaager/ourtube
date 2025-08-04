import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  IconButton,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import FolderOpen from '@mui/icons-material/FolderOpen';
import Folder from '@mui/icons-material/Folder';
import Refresh from '@mui/icons-material/Refresh';
import CheckCircle from '@mui/icons-material/CheckCircle';
import Cancel from '@mui/icons-material/Cancel';
import Download from '@mui/icons-material/Download';
import ContentCopy from '@mui/icons-material/ContentCopy';
import RestartAlt from '@mui/icons-material/RestartAlt';
import { downloadAPI } from '../api';
import { ServerConfig } from '../types';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

export const StatusBar: React.FC = () => {
  const { t } = useTranslation();
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newDirectory, setNewDirectory] = useState('');
  const [updatingYtdlp, setUpdatingYtdlp] = useState(false);
  const [updatingFfmpeg, setUpdatingFfmpeg] = useState(false);
  const [ffmpegDialogOpen, setFfmpegDialogOpen] = useState(false);
  const [ffmpegDialogDismissed, setFfmpegDialogDismissed] = useState(
    localStorage.getItem('ffmpegDialogDismissed') === 'true'
  );
  const [restarting, setRestarting] = useState(false);

  const fetchConfig = async () => {
    try {
      const data = await downloadAPI.getConfig();
      setConfig(data);
      setNewDirectory(data.download_dir);
      
      // Show FFmpeg installation dialog if not installed and not dismissed
      if (!data.ffmpeg_available && !ffmpegDialogDismissed) {
        setFfmpegDialogOpen(true);
      }
    } catch (error) {
      console.error('Config fetch error:', error);
      // For now, set dummy data so the UI works
      setConfig({
        ffmpeg_available: false,
        ffmpeg_version: 'Not installed',
        ffmpeg_updates_available: false,
        max_concurrent_downloads: 3,
        active_downloads: 0,
        ytdl_auto_update: true,
        ytdlp_updates_available: false,
        proxy: false,
        download_dir: './downloads',
        output_template: '%(title)s.%(ext)s',
        supported_sites: 'YouTube and 1000+ other sites via yt-dlp',
        ytdlp_version: '2024.12.23',
        platform: 'linux'
      });
      setNewDirectory('./downloads');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
    // Refresh config every 30 seconds
    const interval = setInterval(fetchConfig, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenFolder = async () => {
    try {
      await downloadAPI.openDownloadDir();
      toast.success(t('notifications.folderOpening'));
    } catch (error) {
      toast.error(t('notifications.folderOpenFailed'));
    }
  };

  const handleChangeDirectory = async () => {
    try {
      await downloadAPI.setDownloadDir(newDirectory);
      toast.success(t('notifications.directoryUpdated'));
      setDialogOpen(false);
      fetchConfig();
    } catch (error) {
      toast.error('Failed to update download directory'); // Keep in English as fallback
    }
  };

  const handleUpdateYtdlp = async () => {
    setUpdatingYtdlp(true);
    try {
      await downloadAPI.updateYtdlp();
      toast.success(t('notifications.ytdlpUpdateTriggered'));
      // Wait a bit then refresh config to get new version
      setTimeout(fetchConfig, 5000);
    } catch (error) {
      toast.error(t('notifications.ytdlpUpdateFailed'));
    } finally {
      setUpdatingYtdlp(false);
    }
  };

  const handleUpdateFfmpeg = async () => {
    setUpdatingFfmpeg(true);
    try {
      await downloadAPI.updateFfmpeg();
      toast.success(t('notifications.ffmpegUpdateTriggered'));
      // Wait a bit then refresh config to get new version
      setTimeout(fetchConfig, 5000);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('notifications.ffmpegUpdateFailed'));
    } finally {
      setUpdatingFfmpeg(false);
    }
  };

  const handleCopyCommand = (command: string) => {
    navigator.clipboard.writeText(command);
    toast.success(t('notifications.commandCopied'));
  };

  const handleDismissFfmpegDialog = (permanent: boolean) => {
    setFfmpegDialogOpen(false);
    if (permanent) {
      localStorage.setItem('ffmpegDialogDismissed', 'true');
      setFfmpegDialogDismissed(true);
    }
  };

  const getPlatformName = (platform: string) => {
    switch (platform) {
      case 'win32': return 'Windows';
      case 'darwin': return 'macOS';
      case 'linux': return 'Linux';
      default: return platform;
    }
  };

  const handleRestart = async () => {
    setRestarting(true);
    try {
      const result = await downloadAPI.restart();
      toast.success(t('notifications.configReloaded'));
      
      // Refresh the config to get updated FFmpeg status
      await fetchConfig();
      
      // If FFmpeg is now available, close the dialog and show success
      if (result.ffmpeg_available) {
        setFfmpegDialogOpen(false);
        toast.success(t('notifications.ffmpegDetected'));
      } else {
        toast.error(t('notifications.ffmpegNotDetected'));
      }
    } catch (error) {
      toast.error(t('notifications.configReloadFailed'));
    } finally {
      setRestarting(false);
    }
  };

  if (loading || !config) {
    return (
      <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
        <Box display="flex" justifyContent="center">
          <CircularProgress size={24} />
        </Box>
      </Paper>
    );
  }

  return (
    <>
      <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
        <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
          {/* Status Indicators */}
          <Box display="flex" gap={1} alignItems="center">
            <Tooltip title={config.ffmpeg_available ? `${t('serverStatus.ffmpegInstalled')} ${t('serverStatus.version')}: ${config.ffmpeg_version}` : t('serverStatus.ffmpegNotInstalled') + ' - ' + t('serverStatus.clickToInstall')}>
              <Chip
                icon={config.ffmpeg_available ? <CheckCircle /> : <Cancel />}
                label={config.ffmpeg_available ? `${t('serverStatus.ffmpegInstalled')} ${config.ffmpeg_version}` : t('serverStatus.ffmpegNotInstalled')}
                color={config.ffmpeg_available ? 'success' : 'error'}
                size="small"
                onClick={!config.ffmpeg_available ? () => setFfmpegDialogOpen(true) : undefined}
                onDelete={config.ffmpeg_available && config.ffmpeg_updates_available ? handleUpdateFfmpeg : undefined}
                deleteIcon={updatingFfmpeg ? <CircularProgress size={16} /> : <Refresh />}
                sx={{ cursor: !config.ffmpeg_available ? 'pointer' : 'default' }}
              />
            </Tooltip>
            
            <Tooltip title={`${t('serverStatus.ytdlpVersion')} ${t('serverStatus.version')}: ${config.ytdlp_version}${config.ytdlp_updates_available ? ` (${t('serverStatus.updateAvailable')})` : ` (${t('serverStatus.upToDate')})`}`}>
              <Chip
                icon={config.ytdlp_updates_available ? <Cancel /> : <CheckCircle />}
                label={`yt-dlp ${config.ytdlp_version}`}
                color={config.ytdlp_updates_available ? 'error' : 'success'}
                size="small"
                onDelete={config.ytdlp_updates_available || !config.ytdl_auto_update ? handleUpdateYtdlp : undefined}
                deleteIcon={updatingYtdlp ? <CircularProgress size={16} /> : <Refresh />}
              />
            </Tooltip>

            {config.ytdl_auto_update && (
              <Chip
                label={t('serverStatus.autoUpdate')}
                color="success"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          {/* Spacer */}
          <Box sx={{ flexGrow: 1 }} />

          {/* Folder Controls */}
          <Box display="flex" gap={1} alignItems="center">
            <Typography variant="body2" color="text.secondary">
              {t('serverStatus.downloads')}: {config.download_dir}
            </Typography>
            
            <Tooltip title={t('serverStatus.changeFolder')}>
              <IconButton size="small" onClick={() => setDialogOpen(true)}>
                <Folder />
              </IconButton>
            </Tooltip>
            
            <Tooltip title={t('serverStatus.openFolder')}>
              <IconButton size="small" onClick={handleOpenFolder}>
                <FolderOpen />
              </IconButton>
            </Tooltip>
          </Box>

          {/* Download Stats */}
          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('serverStatus.active')}: {config.active_downloads}/{config.max_concurrent_downloads}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Directory Change Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('dialogs.changeDirectory.title')}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label={t('dialogs.changeDirectory.label')}
            value={newDirectory}
            onChange={(e) => setNewDirectory(e.target.value)}
            margin="normal"
            helperText={t('dialogs.changeDirectory.helper')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t('dialogs.changeDirectory.cancel')}</Button>
          <Button onClick={handleChangeDirectory} variant="contained">
            {t('dialogs.changeDirectory.change')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* FFmpeg Installation Dialog */}
      <Dialog 
        open={ffmpegDialogOpen} 
        onClose={() => handleDismissFfmpegDialog(false)} 
        maxWidth="sm" 
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <Cancel color="error" />
            {t('dialogs.ffmpegInstallation.title')}
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" paragraph>
            {t('dialogs.ffmpegInstallation.description')}
          </Typography>
          
          <Typography variant="body2" color="text.secondary" paragraph>
            {t('dialogs.ffmpegInstallation.afterInstall')}
          </Typography>
          
          <Typography variant="subtitle2" gutterBottom>
            {t('dialogs.ffmpegInstallation.detectedPlatform')}: <strong>{getPlatformName(config.platform)}</strong>
          </Typography>

          {config.ffmpeg_download_info && (
            <>
              {config.ffmpeg_download_info.package_manager && (
                <Box sx={{ mt: 2, mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    {t('dialogs.ffmpegInstallation.recommendedMethod')}
                  </Typography>
                  <Box 
                    sx={{ 
                      p: 2, 
                      bgcolor: 'grey.100', 
                      borderRadius: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1
                    }}
                  >
                    <code style={{ flex: 1 }}>{config.ffmpeg_download_info.package_manager}</code>
                    <IconButton 
                      size="small" 
                      onClick={() => handleCopyCommand(config.ffmpeg_download_info!.package_manager!)}
                    >
                      <ContentCopy fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>
              )}

              <Typography variant="body2" paragraph sx={{ mt: 2 }}>
                {config.ffmpeg_download_info.instructions}
              </Typography>

              <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center', gap: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<Download />}
                  onClick={() => window.open(config.ffmpeg_download_info!.url, '_blank')}
                  size="large"
                >
                  {t('dialogs.ffmpegInstallation.downloadButton')}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={restarting ? <CircularProgress size={16} /> : <RestartAlt />}
                  onClick={handleRestart}
                  disabled={restarting}
                  size="large"
                >
                  {restarting ? t('dialogs.ffmpegInstallation.checking') : t('dialogs.ffmpegInstallation.checkButton')}
                </Button>
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => handleDismissFfmpegDialog(true)} color="secondary">
            {t('dialogs.ffmpegInstallation.dontShowAgain')}
          </Button>
          <Button onClick={() => handleDismissFfmpegDialog(false)}>
            {t('dialogs.ffmpegInstallation.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};