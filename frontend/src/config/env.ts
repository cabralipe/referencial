const DEFAULT_API_BASE = '/api/v1';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE;
export const APP_TITLE = import.meta.env.VITE_APP_TITLE ?? 'Referencial Curricular';

export function resolveBackendOrigin(): string {
  if (typeof window === 'undefined') {
    return '';
  }

  const explicitOrigin = import.meta.env.VITE_BACKEND_ORIGIN as string | undefined;
  if (explicitOrigin) {
    return explicitOrigin.replace(/\/$/, '');
  }

  if (API_BASE_URL.startsWith('http')) {
    try {
      return new URL(API_BASE_URL).origin;
    } catch (_error) {
      // Segue para os fallbacks abaixo.
    }
  }

  const devBackend = import.meta.env.VITE_DEV_BACKEND_HOST as string | undefined;
  if (import.meta.env.DEV && devBackend) {
    const normalizedHost = devBackend.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    return `${protocol}//${normalizedHost}`;
  }

  if (import.meta.env.DEV && window.location.port === '5173') {
    return 'http://127.0.0.1:8000';
  }

  return window.location.origin;
}

export function buildBackendUrl(path: string): string {
  const origin = resolveBackendOrigin();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${origin}${normalizedPath}`;
}
