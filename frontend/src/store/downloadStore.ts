import { create } from 'zustand';
import { DownloadStatus } from '../types';

interface DownloadStore {
  downloads: DownloadStatus[];
  addDownload: (download: DownloadStatus) => void;
  updateDownload: (id: string, updates: Partial<DownloadStatus>) => void;
  removeDownload: (id: string) => void;
  setDownloads: (downloads: DownloadStatus[]) => void;
}

export const useDownloadStore = create<DownloadStore>((set) => ({
  downloads: [],
  addDownload: (download) =>
    set((state) => ({
      downloads: [download, ...state.downloads],
    })),
  updateDownload: (id, updates) =>
    set((state) => ({
      downloads: state.downloads.map((d) =>
        d.id === id ? { ...d, ...updates } : d
      ),
    })),
  removeDownload: (id) =>
    set((state) => ({
      downloads: state.downloads.filter((d) => d.id !== id),
    })),
  setDownloads: (downloads) => set({ downloads }),
}));