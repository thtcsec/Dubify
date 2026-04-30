import type { AxiosError } from 'axios';

/**
 * Shared error utilities — used across all views.
 */

export function isTimeoutError(error: unknown): boolean {
  const axiosError = error as AxiosError;
  return axiosError.code === 'ECONNABORTED' || String(axiosError.message).includes('timeout');
}

export function extractApiErrorMessage(error: unknown, fallback: string): string {
  const axiosError = error as AxiosError<{ detail?: unknown }>;
  const detail = axiosError.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (detail && typeof detail === 'object') {
    const payload = detail as { message?: string; hints?: string[] };
    if (payload.message && Array.isArray(payload.hints) && payload.hints.length > 0) {
      return `${payload.message} ${payload.hints.join(' ')}`;
    }
    if (payload.message) {
      return payload.message;
    }
  }

  return fallback;
}
