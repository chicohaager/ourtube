import React, { useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  ThemeProvider,
  createTheme,
  CssBaseline,
  IconButton,
  useMediaQuery,
} from '@mui/material';
import Brightness4 from '@mui/icons-material/Brightness4';
import Brightness7 from '@mui/icons-material/Brightness7';
import YouTube from '@mui/icons-material/YouTube';
import { Toaster } from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { DownloadForm } from './components/DownloadForm';
import { DownloadList } from './components/DownloadList';
import { StatusBar } from './components/StatusBar';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { useDownloadStore } from './store/downloadStore';
import { useWebSocket } from './hooks/useWebSocket';
import { downloadAPI } from './api';

function App() {
  const { t } = useTranslation();
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const [darkMode, setDarkMode] = React.useState(prefersDarkMode);
  
  const downloads = useDownloadStore((state) => state.downloads);
  const setDownloads = useDownloadStore((state) => state.setDownloads);
  
  useWebSocket();

  useEffect(() => {
    const fetchDownloads = async () => {
      try {
        const data = await downloadAPI.getAll();
        setDownloads(data);
      } catch (error) {
        console.error('Failed to fetch downloads:', error);
      }
    };

    fetchDownloads();
    const interval = setInterval(fetchDownloads, 5000);
    
    return () => clearInterval(interval);
  }, [setDownloads]);

  const theme = React.useMemo(
    () =>
      createTheme({
        palette: {
          mode: darkMode ? 'dark' : 'light',
          primary: {
            main: '#ff0000',
          },
          secondary: {
            main: '#282828',
          },
        },
        shape: {
          borderRadius: 12,
        },
        typography: {
          fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        },
      }),
    [darkMode]
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static" elevation={0}>
          <Toolbar>
            <LanguageSwitcher />
            <IconButton
              sx={{ ml: 1 }}
              onClick={() => setDarkMode(!darkMode)}
              color="inherit"
            >
              {darkMode ? <Brightness7 /> : <Brightness4 />}
            </IconButton>
          </Toolbar>
        </AppBar>
        
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
          <Box sx={{ mb: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2 }}>
              <img 
                src="/logo.png" 
                alt="Logo" 
                style={{ height: 96, marginRight: 16 }}
              />
              <Typography variant="h4" gutterBottom>
                {t('app.subtitle')}
              </Typography>
            </Box>
            <Typography variant="body1" color="text.secondary" align="center" paragraph>
              {t('app.description')}
            </Typography>
          </Box>
          
          <StatusBar />
          
          <Box sx={{ mb: 4 }}>
            <DownloadForm />
          </Box>
          
          <DownloadList downloads={downloads} />
        </Container>
      </Box>
      
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: darkMode ? '#333' : '#fff',
            color: darkMode ? '#fff' : '#333',
          },
        }}
      />
    </ThemeProvider>
  );
}

export default App;