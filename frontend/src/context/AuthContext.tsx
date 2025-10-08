import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { API_BASE_URL } from '@/config/env';

import {
  clearAuthStorage,
  loadTokens,
  loadUser,
  saveTokens,
  saveUser,
} from './auth-storage';
import type {
  AuthContextValue,
  AuthStatus,
  AuthTokens,
  AuthUser,
  ClienteContextPayload,
  LoginCredentials,
} from './types';

function resolveApiUrl(path: string): string {
  if (path.startsWith('http')) {
    return path;
  }
  if (path.startsWith('/')) {
    return `${API_BASE_URL}${path}`;
  }
  return `${API_BASE_URL}/${path}`;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (data?.detail) {
      if (typeof data.detail === 'string') {
        return data.detail;
      }
      return JSON.stringify(data.detail);
    }
    if (data?.non_field_errors && Array.isArray(data.non_field_errors)) {
      return data.non_field_errors.join(', ');
    }
    return JSON.stringify(data);
  } catch (jsonError) {
    try {
      const text = await response.text();
      if (text) {
        return text;
      }
    } catch (textError) {
      console.warn('Não foi possível extrair detalhe do erro', textError);
    }
  }
  return response.statusText || 'Erro desconhecido';
}

function mapUser(payload: any): AuthUser {
  return {
    id: payload?.id ?? 0,
    email: payload?.email ?? '',
    nome: payload?.nome ?? '',
    role: payload?.role ?? 'leitor',
    clienteId: payload?.cliente_id ?? null,
  };
}

const initialTokens = loadTokens();
const initialUser = loadUser();

interface InternalState {
  status: AuthStatus;
  user: AuthUser | null;
  cliente: ClienteContextPayload | null;
  tokens: AuthTokens;
  error: string | null;
}

const initialState: InternalState = {
  status: initialTokens.accessToken ? 'loading' : 'idle',
  user: initialUser,
  cliente: null,
  tokens: initialTokens,
  error: null,
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<InternalState>(initialState);
  const bootstrapInFlight = useRef(false);

  const logout = useCallback(async () => {
    clearAuthStorage();
    setState({
      status: 'idle',
      user: null,
      cliente: null,
      tokens: {
        accessToken: null,
        refreshToken: null,
      },
      error: null,
    });
  }, []);

  const refreshAccessToken = useCallback(async () => {
    const refreshToken = state.tokens.refreshToken;
    if (!refreshToken) {
      await logout();
      return null;
    }
    try {
      const response = await fetch(resolveApiUrl('/auth/jwt/refresh'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken }),
        credentials: 'include',
      });
      if (!response.ok) {
        await logout();
        return null;
      }
      const data = (await response.json()) as { access: string };
      const newTokens: AuthTokens = {
        accessToken: data.access,
        refreshToken,
      };
      saveTokens(newTokens);
      setState((prev) => ({
        ...prev,
        tokens: newTokens,
      }));
      return data.access;
    } catch (error) {
      console.warn('Falha ao atualizar token de acesso', error);
      await logout();
      return null;
    }
  }, [logout, state.tokens.refreshToken]);

  const authenticatedFetch = useCallback(
    async (path: string, init?: RequestInit, tokenOverride?: string) => {
      const accessToken = tokenOverride ?? state.tokens.accessToken;
      if (!accessToken) {
        throw new Error('Token de acesso indisponível');
      }
      const headers = new Headers(init?.headers ?? {});
      if (!headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${accessToken}`);
      }
      if (!headers.has('Accept')) {
        headers.set('Accept', 'application/json');
      }
      const response = await fetch(resolveApiUrl(path), {
        ...init,
        headers,
        credentials: 'include',
      });
      if (response.status === 401 && !tokenOverride) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          return authenticatedFetch(path, init, refreshed);
        }
      }
      return response;
    },
    [refreshAccessToken, state.tokens.accessToken],
  );

  const fetchCliente = useCallback(
    async (tokenOverride?: string) => {
      const response = await authenticatedFetch('/cliente/me', undefined, tokenOverride);
      if (!response.ok) {
        const message = await extractErrorMessage(response);
        throw new Error(message);
      }
      return (await response.json()) as ClienteContextPayload;
    },
    [authenticatedFetch],
  );

  const refreshCliente = useCallback(async () => {
    try {
      const cliente = await fetchCliente();
      setState((prev) => ({
        ...prev,
        cliente,
        status: prev.status === 'loading' ? 'authenticated' : prev.status,
        error: null,
      }));
    } catch (error) {
      console.warn('Não foi possível atualizar o contexto do cliente', error);
    }
  }, [fetchCliente]);

  const login = useCallback(
    async ({ email, password }: LoginCredentials) => {
      setState((prev) => ({
        ...prev,
        status: 'loading',
        error: null,
      }));
      try {
        const payload = JSON.stringify({ email, password });
        const commonInit: RequestInit = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: payload,
          credentials: 'include',
        };

        const sessionResponse = await fetch(resolveApiUrl('/auth/login'), commonInit);
        if (!sessionResponse.ok) {
          const message = await extractErrorMessage(sessionResponse);
          throw new Error(message || 'Falha ao autenticar');
        }
        const sessionData = (await sessionResponse.json()) as {
          user: any;
          cliente?: ClienteContextPayload;
        };

        const jwtResponse = await fetch(resolveApiUrl('/auth/jwt'), commonInit);
        if (!jwtResponse.ok) {
          const message = await extractErrorMessage(jwtResponse);
          throw new Error(message || 'Não foi possível obter tokens de acesso');
        }
        const jwtData = (await jwtResponse.json()) as { access: string; refresh: string };

        const user = mapUser(sessionData.user);
        const tokens: AuthTokens = {
          accessToken: jwtData.access,
          refreshToken: jwtData.refresh,
        };
        saveTokens(tokens);
        saveUser(user);

        let cliente = sessionData.cliente ?? null;
        if (!cliente) {
          try {
            cliente = await fetchCliente(jwtData.access);
          } catch (clienteError) {
            console.warn('Falha ao carregar contexto do cliente após login', clienteError);
          }
        }

        setState({
          status: 'authenticated',
          user,
          cliente,
          tokens,
          error: null,
        });
      } catch (error) {
        clearAuthStorage();
        const message = error instanceof Error ? error.message : 'Falha ao autenticar';
        setState({
          status: 'error',
          user: null,
          cliente: null,
          tokens: {
            accessToken: null,
            refreshToken: null,
          },
          error: message,
        });
        throw error;
      }
    },
    [fetchCliente],
  );

  useEffect(() => {
    if (bootstrapInFlight.current) {
      return;
    }
    if (
      state.status === 'loading' &&
      state.tokens.accessToken &&
      state.tokens.refreshToken
    ) {
      bootstrapInFlight.current = true;
      fetchCliente()
        .then((cliente) => {
          setState((prev) => ({
            ...prev,
            cliente,
            status: 'authenticated',
            error: null,
          }));
        })
        .catch(async (error) => {
          console.warn('Sessão inválida, limpando credenciais', error);
          await logout();
        })
        .finally(() => {
          bootstrapInFlight.current = false;
        });
    }
  }, [fetchCliente, logout, state.status, state.tokens.accessToken, state.tokens.refreshToken]);

  const getAccessToken = useCallback(() => state.tokens.accessToken, [state.tokens.accessToken]);

  const contextValue: AuthContextValue = useMemo(
    () => ({
      status: state.status,
      isAuthenticated: state.status === 'authenticated' && Boolean(state.user),
      user: state.user,
      cliente: state.cliente,
      tokens: state.tokens,
      error: state.error,
      login,
      logout,
      refreshCliente,
      getAccessToken,
      refreshAccessToken,
    }),
    [
      getAccessToken,
      login,
      logout,
      refreshAccessToken,
      refreshCliente,
      state.cliente,
      state.error,
      state.status,
      state.tokens,
      state.user,
    ],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser utilizado dentro de AuthProvider');
  }
  return context;
}
