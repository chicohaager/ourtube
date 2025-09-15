import { useEffect, useRef, useCallback } from 'react';
import { WebSocketMessage } from '../types';
import { useDownloadStore } from '../store/downloadStore';

export const useWebSocket = () => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const updateDownload = useDownloadStore((state) => state.updateDownload);

  const connect = useCallback(() => {
    // Use relative WebSocket URL to work in both dev and production
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
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
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      wsRef.current = null;
      
      // Implement exponential backoff for reconnection
      if (reconnectAttemptsRef.current < 5) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
        reconnectAttemptsRef.current++;
        
        console.log(`Attempting to reconnect in ${delay}ms...`);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };

    return ws;
  }, [updateDownload]);

  useEffect(() => {
    const ws = connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [connect]);

  return wsRef.current;
};