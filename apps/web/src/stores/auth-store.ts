import { create } from 'zustand';

import type {
  AuthOrganization,
  AuthResult,
  AuthUser,
  TokenPair,
} from '@/types/auth';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  organization: AuthOrganization | null;
  isAuthenticated: boolean;
  setAuth: (result: AuthResult) => void;
  setTokens: (tokens: TokenPair) => void;
  clear: () => void;
}

/**
 * Global authentication store.
 *
 * Holds the current tokens and principal in memory. Tokens are intentionally
 * not persisted to browser storage here; persistence/refresh-on-load is a
 * separate concern handled by the app shell.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  organization: null,
  isAuthenticated: false,
  setAuth: (result: AuthResult): void =>
    set({
      accessToken: result.tokens.access_token,
      refreshToken: result.tokens.refresh_token,
      user: result.user,
      organization: result.organization,
      isAuthenticated: true,
    }),
  setTokens: (tokens: TokenPair): void =>
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    }),
  clear: (): void =>
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      organization: null,
      isAuthenticated: false,
    }),
}));

/** Read the current access token outside React (e.g. in an interceptor). */
export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}
