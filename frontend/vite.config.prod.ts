import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    // Optimize bundle size
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    // Split chunks for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'mui-vendor': ['@mui/material', '@emotion/react', '@emotion/styled'],
          'mui-icons': ['@mui/icons-material/Brightness4', '@mui/icons-material/Brightness7', '@mui/icons-material/YouTube', '@mui/icons-material/Download', '@mui/icons-material/Info', '@mui/icons-material/Cancel', '@mui/icons-material/CheckCircle', '@mui/icons-material/Error', '@mui/icons-material/HourglassEmpty', '@mui/icons-material/CloudDownload', '@mui/icons-material/ClearAll', '@mui/icons-material/VideoLibrary', '@mui/icons-material/AudioFile', '@mui/icons-material/ExpandMore', '@mui/icons-material/ExpandLess', '@mui/icons-material/Language', '@mui/icons-material/FolderOpen', '@mui/icons-material/Folder', '@mui/icons-material/Refresh', '@mui/icons-material/ContentCopy', '@mui/icons-material/RestartAlt'],
          'i18n': ['react-i18next', 'i18next', 'i18next-browser-languagedetector'],
          'utils': ['axios', 'date-fns', 'zustand', 'react-hot-toast'],
        },
      },
    },
    // Increase chunk size warning limit
    chunkSizeWarningLimit: 1000,
    // Enable source maps for production debugging
    sourcemap: true,
    // Assets optimization
    assetsInlineLimit: 4096,
    // CSS code splitting
    cssCodeSplit: true,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['react', 'react-dom', '@mui/material', '@emotion/react', '@emotion/styled'],
  },
})