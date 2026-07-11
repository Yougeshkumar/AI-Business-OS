import { apiClient } from '@/lib/api-client';
import type {
  AuthResult,
  LoginPayload,
  RegisterPayload,
  TokenPair,
} from '@/types/auth';

/** Register a new organization and admin user. */
export async function registerRequest(
  payload: RegisterPayload,
): Promise<AuthResult> {
  const { data } = await apiClient.post<AuthResult>('/auth/register', payload);
  return data;
}

/** Authenticate an existing user. */
export async function loginRequest(payload: LoginPayload): Promise<AuthResult> {
  const { data } = await apiClient.post<AuthResult>('/auth/login', payload);
  return data;
}

/** Rotate a refresh token for a new token pair. */
export async function refreshRequest(refreshToken: string): Promise<TokenPair> {
  const { data } = await apiClient.post<TokenPair>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  return data;
}

/** Revoke a refresh token, ending its session. */
export async function logoutRequest(refreshToken: string): Promise<void> {
  await apiClient.post('/auth/logout', { refresh_token: refreshToken });
}
