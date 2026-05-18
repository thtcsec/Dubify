import axios, { type InternalAxiosRequestConfig } from 'axios';

export const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export const apiOrigin = apiBaseUrl.replace(/\/api\/v1\/?$/, '');

const adminKey = (import.meta.env.VITE_API_ADMIN_KEY || '').trim();

function attachAdminKey(config: InternalAxiosRequestConfig) {
  if (!adminKey) {
    return config;
  }
  config.headers.set('X-API-Key', adminKey);
  return config;
}

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60_000,
});

/** Longer timeout for large video uploads */
export const uploadApi = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30 * 60 * 1000,
});

for (const client of [api, uploadApi]) {
  client.interceptors.request.use(attachAdminKey);
}

export default api;
