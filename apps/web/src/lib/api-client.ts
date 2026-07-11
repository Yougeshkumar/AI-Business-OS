import axios, {
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';

import { env } from '@/lib/env';
import { getAccessToken } from '@/stores/auth-store';

/** Shape of the standard error envelope returned by the API. */
export interface ApiErrorBody {
  code: string;
  message: string;
  details?: string | null;
  trace_id: string;
  timestamp: string;
}

/** Create a configured Axios instance for the AI BOS API. */
function createApiClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: env.apiBaseUrl,
    timeout: 30_000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
      const token = getAccessToken();
      if (token) {
        config.headers.set('Authorization', `Bearer ${token}`);
      }
      return config;
    },
  );

  instance.interceptors.response.use(
    (response: AxiosResponse): AxiosResponse => response,
    (error: unknown): Promise<never> => {
      return Promise.reject(error);
    },
  );

  return instance;
}

export const apiClient = createApiClient();
