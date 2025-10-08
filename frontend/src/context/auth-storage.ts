import type { AuthTokens, AuthUser } from './types';

const TOKEN_KEY = 'referencial:auth:tokens';
const USER_KEY = 'referencial:auth:user';

function isBrowser() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

export function loadTokens(): AuthTokens {
  if (!isBrowser()) {
    return { accessToken: null, refreshToken: null };
  }
  try {
    const raw = window.localStorage.getItem(TOKEN_KEY);
    if (!raw) {
      return { accessToken: null, refreshToken: null };
    }
    const parsed = JSON.parse(raw) as Partial<AuthTokens>;
    return {
      accessToken: parsed.accessToken ?? null,
      refreshToken: parsed.refreshToken ?? null,
    };
  } catch (error) {
    console.warn('Não foi possível carregar tokens armazenados', error);
    return { accessToken: null, refreshToken: null };
  }
}

export function saveTokens(tokens: AuthTokens) {
  if (!isBrowser()) return;
  window.localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export function clearTokens() {
  if (!isBrowser()) return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export function loadUser(): AuthUser | null {
  if (!isBrowser()) {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as AuthUser;
    if (!parsed || !parsed.id) {
      return null;
    }
    return parsed;
  } catch (error) {
    console.warn('Não foi possível carregar usuário armazenado', error);
    return null;
  }
}

export function saveUser(user: AuthUser | null) {
  if (!isBrowser()) return;
  if (!user) {
    window.localStorage.removeItem(USER_KEY);
    return;
  }
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearUser() {
  if (!isBrowser()) return;
  window.localStorage.removeItem(USER_KEY);
}

export function clearAuthStorage() {
  clearTokens();
  clearUser();
}
