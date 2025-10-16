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
  status: 'idle', // Sempre começar como 'idle' e verificar a sessão primeiro
  user: null, // Não carregar usuário do localStorage automaticamente
  cliente: null,
  tokens: initialTokens,
  error: null,
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<InternalState>(initialState);
  const bootstrapInFlight = useRef(false);

  const logout = useCallback(async () => {
    try {
      // Chamar endpoint de logout no backend
      await fetch(resolveApiUrl('/v1/auth/logout'), {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.warn('Erro ao fazer logout no servidor', error);
    }
    
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
    // Para session-based auth, não precisamos de refresh token
    // A sessão é mantida pelos cookies
    return null;
  }, []);

  const authenticatedFetch = useCallback(
    async (path: string, init?: RequestInit) => {
      const headers = new Headers(init?.headers ?? {});
      if (!headers.has('Accept')) {
        headers.set('Accept', 'application/json');
      }
      const response = await fetch(resolveApiUrl(path), {
        ...init,
        headers,
        credentials: 'include', // Importante para session-based auth
      });
      if (response.status === 401) {
        // Se não autorizado, fazer logout
        await logout();
      }
      return response;
    },
    [logout],
  );

  const fetchCliente = useCallback(
    async (tokenOverride?: string) => {
      const response = await authenticatedFetch('/v1/cliente/me', undefined, tokenOverride);
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

  // Função para obter o token CSRF do cookie
  const getCsrfToken = useCallback((): string | null => {
    const name = 'csrftoken';
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop()?.split(';').shift() || null;
    }
    return null;
  }, []);

  const login = useCallback(
    async ({ email, password }: LoginCredentials) => {
      setState((prev) => ({
        ...prev,
        status: 'loading',
        error: null,
      }));
      try {
        // Primeiro, fazer uma requisição para obter o token CSRF
        await fetch(resolveApiUrl('/v1/auth/csrf'), {
          method: 'GET',
          credentials: 'include',
        });

        const csrfToken = getCsrfToken();
        const payload = JSON.stringify({ email, password });
        const commonInit: RequestInit = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            ...(csrfToken && { 'X-CSRFToken': csrfToken }),
          },
          body: payload,
          credentials: 'include',
        };

        const sessionResponse = await fetch(resolveApiUrl('/v1/auth/login'), commonInit);
        if (!sessionResponse.ok) {
          const message = await extractErrorMessage(sessionResponse);
          throw new Error(message || 'Falha ao autenticar');
        }
        const sessionData = (await sessionResponse.json()) as {
          user: any;
          cliente?: ClienteContextPayload;
        };

        const user = mapUser(sessionData.user);
        // Para session-based auth, não precisamos de tokens JWT
        const tokens: AuthTokens = {
          accessToken: null,
          refreshToken: null,
        };
        saveUser(user);

        let cliente = sessionData.cliente ?? null;
        if (!cliente) {
          try {
            cliente = await fetchCliente();
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
    [fetchCliente, getCsrfToken],
  );

  // Verificar sessão atual no início do app
  useEffect(() => {
    if (bootstrapInFlight.current || state.status !== 'idle') {
      return;
    }
    
    const checkSession = async () => {
      bootstrapInFlight.current = true;
      try {
        // Verificar se há uma sessão válida
        const response = await authenticatedFetch('/v1/auth/me');
        if (response.ok) {
          const data = await response.json();
          const user = mapUser(data.user);
          const cliente = data.cliente;
          
          saveUser(user);
          setState({
            status: 'authenticated',
            user,
            cliente,
            tokens: state.tokens,
            error: null,
          });
        } else {
          // Não há sessão válida, limpar dados salvos
          clearAuthStorage();
          setState((prev) => ({
            ...prev,
            status: 'idle',
            user: null,
            cliente: null,
            error: null,
          }));
        }
      } catch (error) {
        // Erro ao verificar sessão, limpar dados
        clearAuthStorage();
        setState((prev) => ({
          ...prev,
          status: 'idle',
          user: null,
          cliente: null,
          error: null,
        }));
      } finally {
        bootstrapInFlight.current = false;
      }
    };

    checkSession();
  }, [authenticatedFetch, state.status, state.tokens]);

  useEffect(() => {
    if (bootstrapInFlight.current) {
      return;
    }
    if (state.status === 'loading' && state.user) {
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
  }, [fetchCliente, logout, state.status, state.user]);

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
