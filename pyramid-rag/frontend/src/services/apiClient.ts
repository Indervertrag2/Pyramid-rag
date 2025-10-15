import axios from 'axios';

const normalizeBaseUrl = (url: string) => url.replace(/\/$/, '');

const resolveBaseUrl = () => {
  const rawEnvUrl = import.meta.env.VITE_API_URL;
  const envUrl = typeof rawEnvUrl === 'string' ? rawEnvUrl.trim() : '';
  if (envUrl && envUrl.toLowerCase() !== 'undefined' && envUrl.toLowerCase() !== 'null') {
    return normalizeBaseUrl(envUrl);
  }

  if (typeof window !== 'undefined' && window.location?.origin) {
    return normalizeBaseUrl(window.location.origin);
  }

  return 'http://localhost:18000';
};

const apiClient = axios.create({
  baseURL: resolveBaseUrl(),
});

apiClient.interceptors.request.use(
  (config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

export default apiClient;



