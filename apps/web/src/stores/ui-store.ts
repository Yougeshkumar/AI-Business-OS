import { create } from 'zustand';

type Theme = 'light' | 'dark' | 'system';

interface UiState {
  sidebarOpen: boolean;
  theme: Theme;
  toggleSidebar: () => void;
  setTheme: (theme: Theme) => void;
}

/** Global UI state store (sidebar, theme). */
export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  theme: 'system',
  toggleSidebar: (): void => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme: Theme): void => set({ theme }),
}));
