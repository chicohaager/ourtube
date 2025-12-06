import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AppSettings, DownloadPreset } from '../types';

const defaultPresets: DownloadPreset[] = [
  {
    id: 'best-video',
    name: 'Best Video',
    quality: 'best',
    audio_only: false,
    subtitles: false,
    subtitle_lang: 'en',
    speed_limit: 0,
    auto_retry: true,
    max_retries: 3,
  },
  {
    id: 'mp3-audio',
    name: 'MP3 Audio',
    quality: 'bestaudio',
    audio_only: true,
    audio_format: 'mp3',
    subtitles: false,
    subtitle_lang: 'en',
    speed_limit: 0,
    auto_retry: true,
    max_retries: 3,
  },
  {
    id: '1080p-subs',
    name: '1080p + Subtitles',
    quality: 'bestvideo[height<=1080]+bestaudio/best',
    audio_only: false,
    subtitles: true,
    subtitle_lang: 'en',
    speed_limit: 0,
    auto_retry: true,
    max_retries: 3,
  },
];

interface SettingsStore extends AppSettings {
  setDarkMode: (darkMode: boolean) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
  setDefaultPreset: (presetId: string | undefined) => void;
  setMaxConcurrentDownloads: (max: number) => void;
  addPreset: (preset: DownloadPreset) => void;
  updatePreset: (id: string, updates: Partial<DownloadPreset>) => void;
  deletePreset: (id: string) => void;
  getPreset: (id: string) => DownloadPreset | undefined;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set, get) => ({
      darkMode: window.matchMedia('(prefers-color-scheme: dark)').matches,
      notificationsEnabled: true,
      defaultPreset: undefined,
      maxConcurrentDownloads: 3,
      presets: defaultPresets,

      setDarkMode: (darkMode) => set({ darkMode }),

      setNotificationsEnabled: (notificationsEnabled) => set({ notificationsEnabled }),

      setDefaultPreset: (defaultPreset) => set({ defaultPreset }),

      setMaxConcurrentDownloads: (maxConcurrentDownloads) => set({ maxConcurrentDownloads }),

      addPreset: (preset) =>
        set((state) => ({
          presets: [...state.presets, preset],
        })),

      updatePreset: (id, updates) =>
        set((state) => ({
          presets: state.presets.map((p) =>
            p.id === id ? { ...p, ...updates } : p
          ),
        })),

      deletePreset: (id) =>
        set((state) => ({
          presets: state.presets.filter((p) => p.id !== id),
          defaultPreset: state.defaultPreset === id ? undefined : state.defaultPreset,
        })),

      getPreset: (id) => get().presets.find((p) => p.id === id),
    }),
    {
      name: 'ourtube-settings',
    }
  )
);

// Helper to request notification permission
export const requestNotificationPermission = async (): Promise<boolean> => {
  if (!('Notification' in window)) {
    return false;
  }

  if (Notification.permission === 'granted') {
    return true;
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }

  return false;
};

// Helper to show notification
export const showNotification = (title: string, body: string, icon?: string) => {
  if (Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: icon || '/logo.png',
      badge: '/logo.png',
    });
  }
};
