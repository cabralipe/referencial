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
import { useQueryClient } from '@tanstack/react-query';

import { API_BASE_URL } from '@/config/env';
import { appendCsrfHeader, ensureCsrfToken, CSRF_HEADER } from '@/api/csrf';

import {
  clearAuthStorage,
  loadActiveClienteId,
  loadTokens,
  loadUser,
  saveActiveClienteId,
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

type AuthPayload = {
  user: any;
  cliente?: ClienteContextPayload;
};

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
  const clientes = Array.isArray(payload?.clientes)
    ? payload.clientes
      .filter((item: any) => Number.isFinite(Number(item?.id)))
      .map((item: any) => ({
        id: Number(item.id),
        nome: String(item?.nome ?? ''),
        slug: String(item?.slug ?? ''),
      }))
    : [];

  return {
    id: payload?.id ?? 0,
    email: payload?.email ?? '',
    nome: payload?.nome ?? '',
    role: payload?.role ?? 'leitor',
    clienteId: payload?.cliente_id ?? null,
    clientes,
    escolaId: payload?.escola_id ?? null,
  };
}

function canAccessCliente(user: AuthUser, clienteId: number | null): boolean {
  if (!clienteId) {
    return false;
  }
  if (user.role === 'super_admin') {
    return true;
  }
  if (user.clienteId === clienteId) {
    return true;
  }
  return user.clientes.some((item) => item.id === clienteId);
}

function getFallbackClienteId(user: AuthUser): number | null {
  if (user.role === 'super_admin') {
    return user.clienteId ?? null;
  }
  if (user.clienteId) {
    return user.clienteId;
  }
  return user.clientes[0]?.id ?? null;
}

function resolveActiveClienteId(
  user: AuthUser | null,
  preferred: number | null | undefined,
  stored: number | null | undefined,
): number | null {
  if (!user) {
    return null;
  }
  if (preferred !== undefined) {
    if (preferred === null) {
      return user.role === 'super_admin' ? null : getFallbackClienteId(user);
    }
    if (canAccessCliente(user, preferred)) {
      return preferred;
    }
  }
  if (stored && canAccessCliente(user, stored)) {
    return stored;
  }
  return getFallbackClienteId(user);
}

const initialTokens = loadTokens();
const initialUser = loadUser();
const storedActiveClienteId = loadActiveClienteId();
const initialActiveClienteId = resolveActiveClienteId(initialUser, undefined, storedActiveClienteId);

interface InternalState {
  status: AuthStatus;
  user: AuthUser | null;
  cliente: ClienteContextPayload | null;
  activeClienteId: number | null;
  tokens: AuthTokens;
  error: string | null;
}

const initialState: InternalState = {
  status: initialTokens.accessToken ? 'loading' : 'idle',
  user: initialUser,
  cliente: null,
  activeClienteId: initialActiveClienteId,
  tokens: initialTokens,
  error: null,
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<InternalState>(initialState);
  const bootstrapInFlight = useRef(false);
  const queryClient = useQueryClient();

  const logout = useCallback(async () => {
    queryClient.clear();
    clearAuthStorage();
    setState({
      status: 'idle',
      user: null,
      cliente: null,
      activeClienteId: null,
      tokens: {
        accessToken: null,
        refreshToken: null,
      },
      error: null,
    });
  }, [queryClient]);

  const refreshAccessToken = useCallback(async () => {
    const refreshToken = state.tokens.refreshToken;
    if (!refreshToken) {
      await logout();
      return null;
    }
    try {
      const response = await fetch(
        resolveApiUrl('/auth/jwt/refresh'),
        appendCsrfHeader({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: JSON.stringify({ refresh: refreshToken }),
          credentials: 'include',
        }),
      );
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
    async (
      path: string,
      init?: RequestInit,
      tokenOverride?: string,
      clienteIdOverride?: number | null,
    ) => {
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

      const clienteId =
        clienteIdOverride === undefined ? state.activeClienteId : clienteIdOverride;
      if (clienteId && !headers.has('X-Cliente-ID')) {
        headers.set('X-Cliente-ID', String(clienteId));
      }

      const response = await fetch(
        resolveApiUrl(path),
        appendCsrfHeader({
          ...init,
          headers,
          credentials: 'include',
        }),
      );
      if (response.status === 401 && !tokenOverride) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          return authenticatedFetch(path, init, refreshed, clienteIdOverride);
        }
      }
      return response;
    },
    [refreshAccessToken, state.activeClienteId, state.tokens.accessToken],
  );

  const fetchAuthMe = useCallback(
    async (tokenOverride?: string, clienteIdOverride?: number | null) => {
      const response = await authenticatedFetch(
        '/auth/me',
        undefined,
        tokenOverride,
        clienteIdOverride,
      );
      if (!response.ok) {
        const message = await extractErrorMessage(response);
        throw new Error(message);
      }
      return (await response.json()) as AuthPayload;
    },
    [authenticatedFetch],
  );

  const fetchCliente = useCallback(
    async (tokenOverride?: string, clienteIdOverride?: number | null) => {
      const response = await authenticatedFetch(
        '/cliente/me',
        undefined,
        tokenOverride,
        clienteIdOverride,
      );
      if (!response.ok) {
        const message = await extractErrorMessage(response);
        throw new Error(message);
      }
      return (await response.json()) as ClienteContextPayload;
    },
    [authenticatedFetch],
  );

  const refreshCliente = useCallback(async () => {
    if (!state.user) {
      return;
    }
    if (state.user.role === 'super_admin' && !state.activeClienteId) {
      setState((prev) => ({ ...prev, cliente: null }));
      return;
    }
    try {
      const cliente = await fetchCliente(undefined, state.activeClienteId);
      setState((prev) => ({
        ...prev,
        cliente,
        status: prev.status === 'loading' ? 'authenticated' : prev.status,
        error: null,
      }));
    } catch (error) {
      console.warn('Não foi possível atualizar o contexto do cliente', error);
      if (state.user.role === 'super_admin') {
        setState((prev) => ({ ...prev, cliente: null }));
      }
    }
  }, [fetchCliente, state.activeClienteId, state.user]);

  const setActiveCliente = useCallback(
    async (clienteId: number | null) => {
      const currentUser = state.user;
      if (!currentUser) {
        return;
      }

      const previousActive = state.activeClienteId;
      const previousCliente = state.cliente;
      const nextActive = resolveActiveClienteId(currentUser, clienteId, state.activeClienteId);

      if (nextActive === previousActive) {
        return;
      }

      saveActiveClienteId(nextActive);
      queryClient.clear();
      setState((prev) => ({
        ...prev,
        activeClienteId: nextActive,
        user: prev.user ? { ...prev.user, clienteId: nextActive } : prev.user,
        cliente: null,
        error: null,
      }));

      try {
        let payload = await fetchAuthMe(undefined, nextActive);
        let userFromServer = mapUser(payload.user);
        let resolvedActive = resolveActiveClienteId(userFromServer, nextActive, nextActive);

        if (resolvedActive !== nextActive) {
          payload = await fetchAuthMe(undefined, resolvedActive);
          userFromServer = mapUser(payload.user);
          resolvedActive = resolveActiveClienteId(userFromServer, resolvedActive, resolvedActive);
        }

        let clienteContext = payload.cliente ?? null;
        if (!clienteContext && resolvedActive) {
          try {
            clienteContext = await fetchCliente(undefined, resolvedActive);
          } catch (clienteError) {
            console.warn('Falha ao recarregar contexto do cliente apos troca', clienteError);
          }
        }

        const nextUser: AuthUser = { ...userFromServer, clienteId: resolvedActive };
        saveUser(nextUser);
        saveActiveClienteId(resolvedActive);
        setState((prev) => ({
          ...prev,
          user: nextUser,
          activeClienteId: resolvedActive,
          cliente: clienteContext,
          status: 'authenticated',
          error: null,
        }));
      } catch (error) {
        saveActiveClienteId(previousActive);
        setState((prev) => ({
          ...prev,
          user: prev.user ? { ...prev.user, clienteId: previousActive } : prev.user,
          activeClienteId: previousActive,
          cliente: previousCliente,
          error: error instanceof Error ? error.message : 'Não foi possível trocar o cliente.',
        }));
      }
    },
    [
      fetchAuthMe,
      fetchCliente,
      queryClient,
      state.activeClienteId,
      state.cliente,
      state.user,
    ],
  );

  const login = useCallback(
    async ({ email, password, role }: LoginCredentials) => {
      queryClient.clear();
      setState((prev) => ({
        ...prev,
        status: 'loading',
        error: null,
      }));
      try {
        await fetch(resolveApiUrl('/auth/csrf'), {
          method: 'GET',
          credentials: 'include',
        });

        const csrfToken = await ensureCsrfToken();
        const payload = JSON.stringify({ email, password, role });
        const commonInit: RequestInit = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            [CSRF_HEADER]: csrfToken,
          },
          body: payload,
          credentials: 'include',
        };

        const sessionResponse = await fetch(resolveApiUrl('/auth/login'), commonInit);
        if (!sessionResponse.ok) {
          const message = await extractErrorMessage(sessionResponse);
          throw new Error(message || 'Falha ao autenticar');
        }
        const sessionData = (await sessionResponse.json()) as AuthPayload;

        const jwtResponse = await fetch(resolveApiUrl('/auth/jwt'), commonInit);
        if (!jwtResponse.ok) {
          const message = await extractErrorMessage(jwtResponse);
          throw new Error(message || 'Não foi possível obter tokens de acesso');
        }
        const jwtData = (await jwtResponse.json()) as { access: string; refresh: string };

        const tokens: AuthTokens = {
          accessToken: jwtData.access,
          refreshToken: jwtData.refresh,
        };
        saveTokens(tokens);

        let authPayload = await fetchAuthMe(jwtData.access, state.activeClienteId);
        let serverUser = mapUser(authPayload.user);
        let activeClienteId = resolveActiveClienteId(
          serverUser,
          state.activeClienteId,
          state.activeClienteId,
        );

        if (activeClienteId !== state.activeClienteId) {
          authPayload = await fetchAuthMe(jwtData.access, activeClienteId);
          serverUser = mapUser(authPayload.user);
          activeClienteId = resolveActiveClienteId(serverUser, activeClienteId, activeClienteId);
        }

        const user: AuthUser = {
          ...serverUser,
          clienteId: activeClienteId,
        };
        saveUser(user);
        saveActiveClienteId(activeClienteId);

        let cliente = authPayload.cliente ?? sessionData.cliente ?? null;
        if (!cliente && activeClienteId) {
          try {
            cliente = await fetchCliente(jwtData.access, activeClienteId);
          } catch (clienteError) {
            console.warn('Falha ao carregar contexto do cliente apos login', clienteError);
          }
        }

        setState({
          status: 'authenticated',
          user,
          cliente,
          activeClienteId,
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
          activeClienteId: null,
          tokens: {
            accessToken: null,
            refreshToken: null,
          },
          error: message,
        });
        throw error;
      }
    },
    [fetchAuthMe, fetchCliente, queryClient, state.activeClienteId],
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
      fetchAuthMe(undefined, state.activeClienteId)
        .then(async (payload) => {
          let authPayload = payload;
          let serverUser = mapUser(authPayload.user);
          let activeClienteId = resolveActiveClienteId(
            serverUser,
            state.activeClienteId,
            state.activeClienteId,
          );

          if (activeClienteId !== state.activeClienteId) {
            authPayload = await fetchAuthMe(undefined, activeClienteId);
            serverUser = mapUser(authPayload.user);
            activeClienteId = resolveActiveClienteId(serverUser, activeClienteId, activeClienteId);
          }

          let cliente = authPayload.cliente ?? null;
          if (!cliente && activeClienteId) {
            try {
              cliente = await fetchCliente(undefined, activeClienteId);
            } catch (err) {
              console.warn('Não foi possível carregar contexto do cliente (ignorando erro)', err);
            }
          }

          const user: AuthUser = {
            ...serverUser,
            clienteId: activeClienteId,
          };
          saveUser(user);
          saveActiveClienteId(activeClienteId);
          setState((prev) => ({
            ...prev,
            user,
            cliente,
            activeClienteId,
            status: 'authenticated',
            error: null,
          }));
        })
        .catch(async (error) => {
          console.warn('Sessao invalida, limpando credenciais', error);
          await logout();
        })
        .finally(() => {
          bootstrapInFlight.current = false;
        });
    }
  }, [
    fetchAuthMe,
    fetchCliente,
    logout,
    state.activeClienteId,
    state.status,
    state.tokens.accessToken,
    state.tokens.refreshToken,
  ]);

  const getAccessToken = useCallback(() => state.tokens.accessToken, [state.tokens.accessToken]);

  const contextValue: AuthContextValue = useMemo(
    () => ({
      status: state.status,
      isAuthenticated: state.status === 'authenticated' && Boolean(state.user),
      user: state.user,
      cliente: state.cliente,
      activeClienteId: state.activeClienteId,
      tokens: state.tokens,
      error: state.error,
      login,
      logout,
      setActiveCliente,
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
      setActiveCliente,
      state.activeClienteId,
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
