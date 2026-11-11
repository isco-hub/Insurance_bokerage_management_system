import axios from 'axios';
import type { ApiError } from '../types';

export const TOKEN_KEY = 'ibms_token';
export const REFRESH_KEY = 'ibms_refresh';

const baseURL = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error?.response?.status === 401 &&
      !String(error?.config?.url || '').includes('auth/login')
    ) {
      window.dispatchEvent(new Event('ibms:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiError | undefined;
    if (data?.message) {
      return typeof data.message === 'string'
        ? data.message
        : JSON.stringify(data.message);
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}

export function resolveOptionLabel(
  item: Record<string, unknown>,
  fieldLabel?: string | ((item: Record<string, unknown>) => string),
): string {
  if (typeof fieldLabel === 'function') return fieldLabel(item);
  if (fieldLabel && item[fieldLabel] != null) return String(item[fieldLabel]);
  const fallbacks = ['name', 'label', 'full_name', 'title', 'policy_number', 'code'];
  for (const key of fallbacks) {
    if (item[key] != null) return String(item[key]);
  }
  return String(item.id ?? '');
}

export async function fetchOptions(
  url: string,
  label?: string | ((item: Record<string, unknown>) => string),
  value = 'id',
): Promise<{ label: string; value: string | number }[]> {
  const ACTIVE_ONLY_URLS = ['/insurers/', '/products/', '/insurance-classes/', '/clients/', '/insurer-branches/'];
  const params: Record<string, unknown> = { pageSize: 500, ordering: 'name' };
  if (ACTIVE_ONLY_URLS.some((u) => url.startsWith(u))) {
    params.is_active = 'true';
  }
  const response = await api.get(url, { params });
  const payload = response.data;
  const items: Record<string, unknown>[] = Array.isArray(payload)
    ? payload
    : payload?.data ?? [];
  return items.map((item) => ({
    label: resolveOptionLabel(item, label),
    value: item[value] as string | number,
  }));
}
// 2026-11-11T15:06:10Z refresh race fix
// 2026-11-11T15:06:10Z 401 redirect
