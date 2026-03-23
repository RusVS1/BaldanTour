import { apiFetch } from './api';

export type User = {
  id: number;
  username: string;
  is_staff: boolean;
  is_superuser: boolean;
};

export function loginApi(username: string, password: string) {
  return apiFetch('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export function logoutApi() {
  return apiFetch('/api/auth/logout/', {
    method: 'POST',
  });
}

export function getMeApi(): Promise<{ user: User }> {
  return apiFetch('/api/auth/me/');
}

export function registerApi(username: string, password: string) {
  return apiFetch('/api/auth/register/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}
