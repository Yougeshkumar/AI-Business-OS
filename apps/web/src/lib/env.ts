/** Public runtime environment values, validated at module load. */

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/v1';

export const env = {
  apiBaseUrl,
} as const;
