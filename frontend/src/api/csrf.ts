import { API_BASE_URL } from '@/config/env';

const CSRF_HEADER_NAME = 'X-CSRFToken';
const CSRF_COOKIE_NAME = 'csrftoken';

function readCsrfTokenFromCookie(): string | null {
  const match = document.cookie.match(new RegExp(`${CSRF_COOKIE_NAME}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function ensureCsrfToken(): Promise<string> {
  const existing = readCsrfTokenFromCookie();
  if (existing) {
    return existing;
  }
  const response = await fetch(`${API_BASE_URL}/auth/csrf`, {
    method: 'GET',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Não foi possível obter o token CSRF');
  }
  const data = (await response.json()) as { csrfToken?: string };
  const token = data.csrfToken ?? readCsrfTokenFromCookie();
  if (!token) {
    throw new Error('Token CSRF indisponível');
  }
  return token;
}

export function appendCsrfHeader(init: RequestInit = {}): RequestInit {
  const token = readCsrfTokenFromCookie();
  if (!token) {
    return init;
  }
  const headers = new Headers(init.headers ?? {});
  if (!headers.has(CSRF_HEADER_NAME)) {
    headers.set(CSRF_HEADER_NAME, token);
  }
  return {
    ...init,
    headers,
  };
}

export const CSRF_HEADER = CSRF_HEADER_NAME;
