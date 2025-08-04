import axios from 'axios';
import { DownloadRequest, DownloadStatus, VideoInfo, ServerConfig } from '../types';

const api = axios.create({
  baseURL: '/api',
});

export const downloadAPI = {
  create: async (request: DownloadRequest) => {
    const response = await api.post<{ download_id: string; status: string }>('/download', request);
    return response.data;
  },

  getAll: async () => {
    const response = await api.get<DownloadStatus[]>('/downloads');
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<DownloadStatus>(`/download/${id}`);
    return response.data;
  },

  cancel: async (id: string) => {
    const response = await api.delete(`/download/${id}`);
    return response.data;
  },

  getVideoInfo: async (url: string) => {
    const response = await api.get<VideoInfo>('/info', { params: { url } });
    return response.data;
  },

  getConfig: async () => {
    const response = await api.get<ServerConfig>('/config');
    return response.data;
  },

  setDownloadDir: async (directory: string) => {
    const response = await api.post('/set-download-dir', { directory });
    return response.data;
  },

  openDownloadDir: async () => {
    const response = await api.post('/open-download-dir');
    return response.data;
  },

  updateYtdlp: async () => {
    const response = await api.post('/update-ytdlp');
    return response.data;
  },

  updateFfmpeg: async () => {
    const response = await api.post('/update-ffmpeg');
    return response.data;
  },

  restart: async () => {
    const response = await api.post('/restart');
    return response.data;
  },

  clearHistory: async () => {
    const response = await api.delete('/downloads');
    return response.data;
  },

};