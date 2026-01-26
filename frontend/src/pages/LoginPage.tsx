import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation, type Location } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import { type RoleOption } from '@/components/login/roles';

const ROLE_REDIRECTS: Record<RoleOption, string> = {
  membro_gt: '/inicio',
  revisor: '/revisor/inbox',
  articulador: '/redator/revisoes',
};

const isValidEmail = (value: string) => /\S+@\S+\.\S+/.test(value);

const resolveLoginError = (err: unknown) => {
  if (err instanceof ApiError) {
    if (err.message.includes('perfil selecionado')) {
      return 'Seu usuário não possui acesso ao perfil selecionado.';
    }
    if (err.message.toLowerCase().includes('credenciais')) {
      return 'E-mail ou senha inválidos. Tente novamente.';
    }
    return err.message;
  }
  if (err instanceof Error) {
    const message = err.message || '';
    if (message.toLowerCase().includes('perfil selecionado')) {
      return 'Seu usuário não possui acesso ao perfil selecionado.';
    }
    if (message.toLowerCase().includes('credenciais')) {
      return 'E-mail ou senha inválidos. Tente novamente.';
    }
    if (!navigator.onLine || message.toLowerCase().includes('failed to fetch')) {
      return 'Não foi possível conectar. Verifique sua internet.';
    }
    return message;
  }
  return 'Não foi possível autenticar.';
};

const trackLoginEvent = (event: string, payload?: Record<string, unknown>) => {
  const data = {
    ...payload,
    timestamp: new Date().toISOString(),
  };
  const anyWindow = window as typeof window & {
    analytics?: { track?: (name: string, props?: Record<string, unknown>) => void };
    gtag?: (...args: unknown[]) => void;
  };
  if (anyWindow.analytics?.track) {
    anyWindow.analytics.track(event, data);
    return;
  }
  if (anyWindow.gtag) {
    anyWindow.gtag('event', event, data);
    return;
  }
  console.debug('[telemetry]', event, data);
};

export function LoginPage() {
  const queryClient = useQueryClient();
  const { isAuthenticated, login, status, error, user } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [submitAttempted, setSubmitAttempted] = useState(false);

  useEffect(() => {
    queryClient.clear();
  }, [queryClient]);

  const redirectTo = (location.state as { from?: Location })?.from?.pathname ?? null;

  const emailError = useMemo(() => {
    if (!email.trim()) return 'Este campo é obrigatório.';
    if (!isValidEmail(email)) return 'Informe um e-mail válido.';
    return null;
  }, [email]);

  const passwordError = useMemo(() => {
    if (!password.trim()) return 'Este campo é obrigatório.';
    return null;
  }, [password]);

  const isFormValid = !emailError && !passwordError;

  if (isAuthenticated) {
    const roleKey = (user?.role ?? '') as RoleOption;
    const roleRedirect = ROLE_REDIRECTS[roleKey] ?? '/';
    return <Navigate to={redirectTo ?? roleRedirect} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitAttempted(true);
    setLocalError(null);

    if (!isFormValid) {
      return;
    }

    setIsSubmitting(true);
    const startedAt = performance.now();
    trackLoginEvent('login_attempt');

    try {
      await login({ email, password });
      const durationMs = Math.round(performance.now() - startedAt);
      trackLoginEvent('login_success', { durationMs });
    } catch (err) {
      const message = resolveLoginError(err);
      setLocalError(message);
      const durationMs = Math.round(performance.now() - startedAt);
      const failureType = message.includes('perfil selecionado')
        ? 'perfil'
        : message.includes('senha inválidos')
          ? 'credenciais'
          : message.includes('internet')
            ? 'offline'
            : 'erro';
      trackLoginEvent('login_failure', { durationMs, type: failureType });
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeError = localError ?? error;
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-display antialiased">
      <div className="min-h-screen grid lg:grid-cols-[1.1fr_0.9fr]">
        <section className="relative overflow-hidden bg-gradient-to-br from-sky-600 via-blue-600 to-cyan-500 text-white px-8 py-10 lg:px-16 lg:py-16">
          <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-white/10 blur-3xl"></div>
          <div className="absolute bottom-0 right-0 h-72 w-72 translate-x-1/3 translate-y-1/3 rounded-full bg-cyan-200/30 blur-3xl"></div>

          <div className="relative z-10 max-w-xl space-y-8">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-2xl bg-white/15 border border-white/30 flex items-center justify-center">
                <span className="material-symbols-outlined text-3xl">school</span>
              </div>
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-white/70">MEB Referencial</p>
                <h1 className="text-3xl font-bold">Ambiente de produção editorial</h1>
              </div>
            </div>

            <p className="text-lg text-white/90">
              Uma plataforma para criar, revisar e publicar textos com clareza e organização desde a primeira etapa.
            </p>

            <div className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-white/70">O que você encontra aqui</h2>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-xl">check_circle</span>
                  <span>Trilhas guiadas por etapa: passo a passo</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-xl">check_circle</span>
                  <span>Textos colaborativos com revisão e histórico</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-xl">check_circle</span>
                  <span>Mural com avisos e materiais de apoio</span>
                </li>
              </ul>
            </div>

            <div className="rounded-3xl border border-white/20 bg-white/10 p-6">
              <div className="h-40 rounded-2xl border border-dashed border-white/30 bg-white/5" aria-hidden="true"></div>
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-10 lg:px-12">
          <div className="w-full max-w-xl">
            <div className="rounded-3xl bg-white shadow-xl border border-slate-200/60 p-8">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold text-slate-900">Acessar</h2>
                <p className="text-slate-500">Entre com suas credenciais</p>
              </div>

              <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-slate-700" htmlFor="login-email">
                    E-mail
                  </label>
                  <input
                    id="login-email"
                    className={`w-full h-12 px-4 bg-white border rounded-xl focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 text-slate-900 placeholder-slate-400 transition-all outline-none ${
                      (submitAttempted || touched.email) && emailError
                        ? 'border-red-300'
                        : 'border-slate-200'
                    }`}
                    placeholder="nome@dominio.com"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setLocalError(null);
                    }}
                    onBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
                    aria-describedby={
                      (submitAttempted || touched.email) && emailError ? 'login-email-error' : undefined
                    }
                    required
                    autoComplete="email"
                  />
                  {(submitAttempted || touched.email) && emailError && (
                    <p id="login-email-error" className="text-sm text-red-600">
                      {emailError}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-semibold text-slate-700" htmlFor="login-password">
                      Senha
                    </label>
                    <a className="text-xs font-semibold text-sky-600 hover:text-sky-700" href="#">
                      Esqueceu a senha?
                    </a>
                  </div>
                  <div className="relative">
                    <input
                      id="login-password"
                      className={`w-full h-12 px-4 pr-12 bg-white border rounded-xl focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500 text-slate-900 placeholder-slate-400 transition-all outline-none ${
                        (submitAttempted || touched.password) && passwordError
                          ? 'border-red-300'
                          : 'border-slate-200'
                      }`}
                      placeholder="••••••••"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        setLocalError(null);
                      }}
                      onBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
                      aria-describedby={
                        (submitAttempted || touched.password) && passwordError
                          ? 'login-password-error'
                          : undefined
                      }
                      required
                      autoComplete="current-password"
                    />
                    <button
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    >
                      <span className="material-symbols-outlined text-[20px]">
                        {showPassword ? 'visibility' : 'visibility_off'}
                      </span>
                    </button>
                  </div>
                  {(submitAttempted || touched.password) && passwordError && (
                    <p id="login-password-error" className="text-sm text-red-600">
                      {passwordError}
                    </p>
                  )}
                </div>

                {activeError && (
                  <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                    {activeError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!isFormValid || isSubmitting || status === 'loading'}
                  className="w-full h-12 rounded-xl bg-sky-600 text-white font-semibold shadow-lg shadow-sky-500/20 disabled:opacity-60 disabled:cursor-not-allowed hover:bg-sky-700 transition-colors"
                >
                  {isSubmitting || status === 'loading' ? (
                    <span className="inline-flex items-center justify-center gap-2">
                      <span
                        className="h-4 w-4 animate-spin rounded-full border-2 border-white/60 border-t-transparent"
                        aria-hidden="true"
                      ></span>
                      Entrando...
                    </span>
                  ) : (
                    'Entrar'
                  )}
                </button>
              </form>
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400">
              <a className="hover:text-slate-600" href="#">Ajuda</a>
              <a className="hover:text-slate-600" href="#">Privacidade</a>
              <a className="hover:text-slate-600" href="#">Termos</a>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
