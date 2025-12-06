import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  LinearProgress,
  IconButton,
  Chip,
  Box,
  Typography,
  Paper,
  Tooltip,
  Button,
} from '@mui/material';
import Cancel from '@mui/icons-material/Cancel';
import CheckCircle from '@mui/icons-material/CheckCircle';
import Error from '@mui/icons-material/Error';
import HourglassEmpty from '@mui/icons-material/HourglassEmpty';
import CloudDownload from '@mui/icons-material/CloudDownload';
import ClearAll from '@mui/icons-material/ClearAll';
import Speed from '@mui/icons-material/Speed';
import Schedule from '@mui/icons-material/Schedule';
import Refresh from '@mui/icons-material/Refresh';
import AccessTime from '@mui/icons-material/AccessTime';
import { format } from 'date-fns';
import { DownloadStatus } from '../types';
import { useDownloadStore } from '../store/downloadStore';
import { downloadAPI } from '../api';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

const statusIcons: Record<string, React.ReactNode> = {
  queued: <HourglassEmpty />,
  downloading: <CloudDownload />,
  processing: <CloudDownload />,
  completed: <CheckCircle color="success" />,
  failed: <Error color="error" />,
  cancelled: <Cancel color="warning" />,
  scheduled: <AccessTime color="info" />,
  retrying: <Refresh color="warning" />,
};

const statusColors: Record<string, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
  queued: 'default',
  downloading: 'primary',
  processing: 'primary',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
  scheduled: 'info',
  retrying: 'warning',
};

interface DownloadListProps {
  downloads: DownloadStatus[];
}

export const DownloadList: React.FC<DownloadListProps> = ({ downloads }) => {
  const { t } = useTranslation();
  const updateDownload = useDownloadStore((state) => state.updateDownload);
  const setDownloads = useDownloadStore((state) => state.setDownloads);

  const handleCancel = async (id: string) => {
    try {
      await downloadAPI.cancel(id);
      updateDownload(id, { status: 'cancelled' });
      toast.success(t('queue.downloadCancelled'));
    } catch (error) {
      toast.error(t('queue.failedToCancel'));
    }
  };

  const handleClearHistory = async () => {
    try {
      await downloadAPI.clearHistory();
      setDownloads([]);
      toast.success(t('queue.historyCleared'));
    } catch (error) {
      toast.error(t('queue.failedToClearHistory'));
    }
  };

  // Sort downloads by creation date (newest first)
  const sortedDownloads = [...downloads].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  if (downloads.length === 0) {
    return (
      <Paper elevation={3} sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          {t('queue.noDownloads')}
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={3}>
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" gutterBottom>
          {t('queue.title')} ({downloads.length})
        </Typography>
        {downloads.length > 0 && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<ClearAll />}
            onClick={handleClearHistory}
            color="secondary"
          >
            {t('queue.clearAll')}
          </Button>
        )}
      </Box>
      
      <List>
        {sortedDownloads.map((download) => (
          <ListItem
            key={download.id}
            sx={{
              borderBottom: '1px solid',
              borderColor: 'divider',
              '&:last-child': { borderBottom: 'none' },
            }}
            secondaryAction={
              ['downloading', 'queued', 'scheduled', 'retrying'].includes(download.status) ? (
                <Tooltip title={t('queue.cancelDownload')}>
                  <IconButton edge="end" onClick={() => handleCancel(download.id)}>
                    <Cancel />
                  </IconButton>
                </Tooltip>
              ) : null
            }
          >
            <Box sx={{ mr: 2 }}>{statusIcons[download.status]}</Box>
            
            <ListItemText
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body1" noWrap sx={{ maxWidth: 400 }}>
                    {download.filename || download.url}
                  </Typography>
                  <Chip
                    label={t(`status.${download.status}`)}
                    size="small"
                    color={statusColors[download.status]}
                  />
                </Box>
              }
              secondary={
                <Box>
                  {download.status === 'downloading' && download.progress !== undefined && (
                    <Box sx={{ mt: 1.5 }}>
                      {/* Progress Bar */}
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Box sx={{ width: '100%', mr: 2 }}>
                          <LinearProgress
                            variant="determinate"
                            value={download.progress}
                            sx={{
                              height: 8,
                              borderRadius: 4,
                              backgroundColor: 'rgba(0, 0, 0, 0.1)',
                              '& .MuiLinearProgress-bar': {
                                backgroundColor: '#4caf50',
                                borderRadius: 4,
                              },
                            }}
                          />
                        </Box>
                        <Box sx={{ minWidth: 50 }}>
                          <Typography variant="body1" fontWeight="bold" color="primary">
                            {Math.round(download.progress)}%
                          </Typography>
                        </Box>
                      </Box>
                      
                      {/* Speed and ETA */}
                      {(download.speed || download.eta) && (
                        <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
                          {download.speed && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Speed sx={{ fontSize: 16, color: 'primary.main' }} />
                              <Typography variant="body2" fontWeight="medium" color="primary">
                                {t('progress.speed')}: {download.speed}
                              </Typography>
                            </Box>
                          )}
                          {download.eta && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Schedule sx={{ fontSize: 16, color: 'primary.main' }} />
                              <Typography variant="body2" fontWeight="medium" color="primary">
                                {t('progress.eta')}: {download.eta}
                              </Typography>
                            </Box>
                          )}
                        </Box>
                      )}
                    </Box>
                  )}
                  
                  {/* Scheduled time info */}
                  {download.status === 'scheduled' && download.scheduled_time && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                      <Schedule sx={{ fontSize: 16, color: 'info.main' }} />
                      <Typography variant="body2" color="info.main">
                        {t('status.scheduledFor')}: {format(new Date(download.scheduled_time), 'PPp')}
                      </Typography>
                    </Box>
                  )}

                  {/* Retry info */}
                  {download.status === 'retrying' && download.retry_count !== undefined && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
                      <Refresh sx={{ fontSize: 16, color: 'warning.main' }} />
                      <Typography variant="body2" color="warning.main">
                        {t('status.retryAttempt')} {download.retry_count}/{download.max_retries || 3}
                      </Typography>
                    </Box>
                  )}

                  {download.error && (
                    <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                      {t('status.error')}: {download.error}
                    </Typography>
                  )}

                  <Typography variant="caption" color="text.secondary">
                    {t('status.started')}: {format(new Date(download.created_at), 'PPp')}
                    {download.completed_at && ` • ${t('status.completedAt')}: ${format(new Date(download.completed_at), 'PPp')}`}
                  </Typography>
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};