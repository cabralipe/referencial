import { useCallback } from 'react';

import { API_BASE_URL } from '@/config/env';
import { appendCsrfHeader } from '@/api/csrf';
import { useAuth } from '@/context/AuthContext';

// Função para obter o token CSRF do cookie
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

export interface RequestOptions {
  query?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
  ifMatch?: string;
  skipAuth?: boolean;
  responseType?: 'json' | 'text' | 'blob' | 'arrayBuffer';
  signal?: AbortSignal;
}

export interface ApiResponse<T> {
  data: T;
  etag?: string;
  status: number;
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const base = path.startsWith('http')
    ? path
    : `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const url = new URL(base, window.location.origin);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }
  return url.toString();
}

async function parseResponse<T>(response: Response, responseType: RequestOptions['responseType']): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  const type = responseType ?? 'json';
  if (type === 'json') {
    return (await response.json()) as T;
  }
  if (type === 'text') {
    return (await response.text()) as T;
  }
  if (type === 'blob') {
    return (await response.blob()) as T;
  }
  if (type === 'arrayBuffer') {
    return (await response.arrayBuffer()) as T;
  }
  throw new Error(`Tipo de resposta não suportado: ${type}`);
}

async function extractApiError(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (jsonError) {
    try {
      return await response.text();
    } catch (textError) {
      return response.statusText;
    }
  }
}

export function useApiClient() {
  const { getAccessToken, refreshAccessToken, logout, user } = useAuth();

  const request = useCallback(
    async <T,>(method: string, path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> => {
      const url = buildUrl(path, options.query);
      const headers = new Headers(options.headers ?? {});

      if (!options.skipAuth) {
        const accessToken = getAccessToken();
        if (accessToken) {
          headers.set('Authorization', `Bearer ${accessToken}`);
        }
      }

      if (!headers.has('Accept')) {
        headers.set('Accept', 'application/json');
      }

      // Adicionar X-Cliente-ID automaticamente para super_admin quando necessário
      if (user?.role === 'super_admin' && !headers.has('X-Cliente-ID')) {
        // Mapeamento GT -> Cliente baseado nos dados do sistema
        const gtClienteMap: Record<string, string> = {
          '1': '2', // GT 1 pertence ao Cliente 2 (jeremias da silva)
          '2': '3', // GT 2 pertence ao Cliente 3 (São miguel dos Campos)
          '3': '1', // GT 3 pertence ao Cliente 1 (Cliente de Teste)
        };
        
        // Para respostas, verificar se há um gt_id nos parâmetros de query ou no body
        const gtId = options.query?.gt || options.query?.gt_id || 
                    (options.body && typeof options.body === 'object' && 
                     (options.body as any)?.gt);
        
        if (gtId && path.includes('/respostas')) {
          const clienteId = gtClienteMap[String(gtId)];
          if (clienteId) {
            headers.set('X-Cliente-ID', clienteId);
          }
        }
      }

      // Adicionar token CSRF para métodos que modificam dados
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
        const csrfToken = getCsrfToken();
        if (csrfToken) {
          headers.set('X-CSRFToken', csrfToken);
        }
      }

      let body: BodyInit | undefined;
      if (options.body !== undefined && options.body !== null) {
        if (!(options.body instanceof FormData)) {
          if (!headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
          }
          if (headers.get('Content-Type')?.includes('application/json')) {
            body = JSON.stringify(options.body);
          } else {
            body = options.body as BodyInit;
          }
        } else {
          body = options.body;
        }
      }

      if (options.ifMatch) {
        headers.set('If-Match', options.ifMatch);
      }

      let init: RequestInit = {
        method,
        headers,
        body,
        signal: options.signal,
        credentials: 'include',
      };

      if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method.toUpperCase())) {
        init = appendCsrfHeader(init);
      }

      let response = await fetch(url, init);

      if (response.status === 401 && !options.skipAuth) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          headers.set('Authorization', `Bearer ${refreshed}`);
          response = await fetch(url, init);
        } else {
          await logout();
          throw new ApiError('Sessão expirada', response.status);
        }
      }

      if (!response.ok) {
        const payload = await extractApiError(response);
        const message =
          typeof payload === 'string'
            ? payload
            : (payload as { detail?: string })?.detail ?? 'Erro na requisição';
        throw new ApiError(message, response.status, payload);
      }

      const etag = response.headers.get('ETag') ?? undefined;
      const data = await parseResponse<T>(response, options.responseType);

      return {
        data,
        etag,
        status: response.status,
      };
    },
    [getAccessToken, logout, refreshAccessToken, user],
  );

  const get = useCallback(
    async <T,>(path: string, options?: RequestOptions) => request<T>('GET', path, options),
    [request],
  );

  const post = useCallback(
    async <T,>(path: string, options?: RequestOptions) => request<T>('POST', path, options),
    [request],
  );

  const put = useCallback(
    async <T,>(path: string, options?: RequestOptions) => request<T>('PUT', path, options),
    [request],
  );

  const patch = useCallback(
    async <T,>(path: string, options?: RequestOptions) => request<T>('PATCH', path, options),
    [request],
  );

  const del = useCallback(
    async <T,>(path: string, options?: RequestOptions) => request<T>('DELETE', path, options),
    [request],
  );

  return { request, get, post, put, patch, del };
}
