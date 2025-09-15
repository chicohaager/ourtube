import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Typography,
  Box,
  CircularProgress,
  Breadcrumbs,
  Link,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ComputerIcon from '@mui/icons-material/Computer';
import HomeIcon from '@mui/icons-material/Home';
import { downloadAPI } from '../api';
import { DirectoryItem } from '../types';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';

interface DirectoryPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
  currentPath?: string;
  title: string;
}

export const DirectoryPicker: React.FC<DirectoryPickerProps> = ({
  open,
  onClose,
  onSelect,
  currentPath = '/',
  title
}) => {
  const { t } = useTranslation();
  const [directories, setDirectories] = useState<DirectoryItem[]>([]);
  const [currentDir, setCurrentDir] = useState<string>(currentPath);
  const [loading, setLoading] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string>(currentPath);

  const loadDirectories = async (path: string) => {
    setLoading(true);
    try {
      const response = await downloadAPI.browseDirectories(path);
      setDirectories(response.directories);
      setCurrentDir(response.currentPath || path);
    } catch (error) {
      console.error('Failed to load directories:', error);
      toast.error(t('dialogs.directoryPicker.loadError'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      setSelectedPath(currentPath);
      loadDirectories(currentPath);
    }
  }, [open, currentPath]);

  const handleDirectoryClick = (directory: DirectoryItem) => {
    if (directory.isParent) {
      loadDirectories(directory.path);
    } else {
      loadDirectories(directory.path);
    }
  };

  const handleDirectorySelect = (directory: DirectoryItem) => {
    setSelectedPath(directory.path);
  };

  const handleConfirm = () => {
    onSelect(selectedPath);
    onClose();
  };

  const getBreadcrumbs = () => {
    if (!currentDir || currentDir === '/') return [];

    const parts = currentDir.split(/[/\\]/).filter(Boolean);
    const breadcrumbs = [];
    let path = '';

    // Check if this looks like a Windows path (has drive letter)
    const isWindowsPath = parts.length > 0 && parts[0].match(/^[A-Za-z]:$/);

    if (isWindowsPath) {
      breadcrumbs.push({
        label: parts[0],
        path: parts[0] + '\\'
      });
      parts.shift();
      path = breadcrumbs[0].path;
    } else {
      // Add root for Unix-like systems
      breadcrumbs.push({
        label: 'Root',
        path: '/'
      });
      path = '/';
    }

    // Add remaining path parts
    for (const part of parts) {
      path += (path.endsWith('/') || path.endsWith('\\')) ? part : '/' + part;
      breadcrumbs.push({
        label: part,
        path: path
      });
    }

    return breadcrumbs;
  };

  const getIcon = (directory: DirectoryItem) => {
    if (directory.isParent) return <ArrowUpwardIcon />;
    if (directory.isRoot) return <ComputerIcon />;
    return selectedPath === directory.path ? <FolderOpenIcon /> : <FolderIcon />;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent sx={{ minHeight: 400 }}>
        {/* Breadcrumbs */}
        <Box sx={{ mb: 2 }}>
          <Breadcrumbs aria-label="directory breadcrumb">
            <Link
              component="button"
              variant="body2"
              onClick={() => loadDirectories('/')}
              sx={{ display: 'flex', alignItems: 'center' }}
            >
              <HomeIcon sx={{ mr: 0.5 }} fontSize="inherit" />
              Root
            </Link>
            {getBreadcrumbs().slice(1).map((crumb, index) => (
              <Link
                key={index}
                component="button"
                variant="body2"
                onClick={() => loadDirectories(crumb.path)}
                color={index === getBreadcrumbs().length - 2 ? 'text.primary' : 'inherit'}
              >
                {crumb.label}
              </Link>
            ))}
          </Breadcrumbs>
        </Box>

        {/* Current Path Display */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('dialogs.directoryPicker.selectedPath')}: {selectedPath}
        </Typography>

        {/* Directory List */}
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, minHeight: 300 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
              <CircularProgress />
            </Box>
          ) : directories.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
              <Typography color="text.secondary">
                {t('dialogs.directoryPicker.noDirectories')}
              </Typography>
            </Box>
          ) : (
            <List dense>
              {directories.map((directory, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemButton
                    selected={selectedPath === directory.path}
                    onClick={() => handleDirectorySelect(directory)}
                    onDoubleClick={() => handleDirectoryClick(directory)}
                  >
                    <ListItemIcon>
                      {getIcon(directory)}
                    </ListItemIcon>
                    <ListItemText
                      primary={directory.name}
                      primaryTypographyProps={{
                        fontWeight: directory.isParent ? 'bold' : 'normal'
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {t('dialogs.directoryPicker.hint')}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          {t('dialogs.directoryPicker.cancel')}
        </Button>
        <Button onClick={handleConfirm} variant="contained" disabled={!selectedPath}>
          {t('dialogs.directoryPicker.select')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};