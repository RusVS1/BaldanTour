function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

export class ApiError extends Error {
  data?: unknown;

  constructor(message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.data = data;
  }
}

export async function apiFetch<T = unknown>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken') ?? '',
      ...(options.headers || {}),
    },
    ...options,
  });

  let data: unknown = null;

  try {
    data = await res.json();
  } catch {
    console.warn('Response is not JSON');
  }

  if (!res.ok) {
    const message = extractErrorMessage(data);
    throw new ApiError(message, data);
  }

  return data as T;
}

function toSafeString(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return '';
    return toSafeString(value[0]);
  }
  const str = String(value);
  if (str !== '[object Object]') return str;
  return '';
}

function extractErrorMessage(data: unknown): string {
  if (typeof data !== 'object' || data === null) {
    return 'Ошибка запроса';
  }

  if ('detail' in data) {
    const detail = toSafeString(data.detail);
    if (detail) return detail;
  }

  if ('message' in data) {
    const message = toSafeString(data.message);
    if (message) return message;
  }

  if ('error' in data) {
    const error = toSafeString(data.error);
    if (error) return error;
  }

  for (const [key, value] of Object.entries(data)) {
    if (['detail', 'message', 'error', 'status_code'].includes(key)) continue;
    if (Array.isArray(value) && value.length > 0) {
      const fieldError = toSafeString(value[0]);
      if (fieldError) return fieldError;
    }
  }

  if ('non_field_errors' in data && Array.isArray(data.non_field_errors)) {
    const nonField = toSafeString(data.non_field_errors[0]);
    if (nonField) return nonField;
  }

  return 'Ошибка запроса';
}
