import { defineBoot } from '#q-app/wrappers';
import axios, { type AxiosInstance } from 'axios';

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

// Используем относительный путь, чтобы запросы перехватывал Nginx
const api = axios.create({ 
  baseURL: '/api/',  // <-- Ключевое изменение
  withCredentials: true  // <-- Важно для cookie-аутентификации
});

export default defineBoot(({ app }) => {
  app.config.globalProperties.$axios = axios;
  app.config.globalProperties.$api = api;
});

export { api };