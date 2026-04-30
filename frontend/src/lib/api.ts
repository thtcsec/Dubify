import axios from 'axios';

export const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export const apiOrigin = apiBaseUrl.replace(/\/api\/v1\/?$/, '');

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60000, // 60 seconds default (uploads may take longer)
});

export default api;
