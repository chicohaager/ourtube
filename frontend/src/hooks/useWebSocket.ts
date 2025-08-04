import { useEffect, useRef } from 'react';
import { WebSocketMessage } from '../types';
import { useDownloadStore } from '../store/downloadStore';

export const useWebSocket = () => {
  const wsRef = useRef<WebSocket | null>(null);
  const updateDownload = useDownloadStore((state) => state.updateDownload);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'progress':
          updateDownload(message.download_id, { 
            progress: message.progress,
            speed: message.speed,
            eta: message.eta
          });
          break;
        case 'status':
          updateDownload(message.download_id, { status: message.status as any });
          break;
        case 'completed':
          updateDownload(message.download_id, { 
            status: 'completed', 
            progress: 100,
            filename: message.filename 
          });
          break;
        case 'error':
          updateDownload(message.download_id, { 
            status: 'failed', 
            error: message.error 
          });
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      ws.close();
    };
  }, [updateDownload]);

  return wsRef.current;
};