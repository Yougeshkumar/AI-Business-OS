import axios from 'axios';

import { env } from '@/lib/env';

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
}

/** Base origin of the API (strips the trailing /v1 path segment). */
function apiOrigin(): string {
  try {
    const url = new URL(env.apiBaseUrl);
    return `${url.protocol}//${url.host}`;
  } catch {
    return env.apiBaseUrl;
  }
}

/** Fetch the API liveness status from the root /health endpoint. */
export async function fetchHealth(): Promise<HealthStatus> {
  const { data } = await axios.get<HealthStatus>(`${apiOrigin()}/health`, {
    timeout: 10_000,
  });
  return data;
}
