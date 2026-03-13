export type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'error';

export interface AuthTokens {
  accessToken: string | null;
  refreshToken: string | null;
}

export interface AuthUser {
  id: number;
  email: string;
  nome: string;
  role: string;
  clienteId: number | null;
  escolaId?: number | null;
}

export interface ClienteContextPayload {
  cliente: {
    id: number;
    nome: string;
    slug: string;
  };
  configs: Record<string, string>;
  flags: Record<string, boolean>;
  tema: {
    logo_url?: string;
    meb_avatar_url?: string;
    cor_primaria?: string;
    cor_secundaria?: string;
    rodape_html?: string;
    cabecalho_html?: string;
  };
}

export interface LoginCredentials {
  email: string;
  password: string;
  role?: string;
}

export interface AuthContextValue {
  status: AuthStatus;
  isAuthenticated: boolean;
  user: AuthUser | null;
  cliente: ClienteContextPayload | null;
  tokens: AuthTokens;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshCliente: () => Promise<void>;
  getAccessToken: () => string | null;
  refreshAccessToken: () => Promise<string | null>;
}
