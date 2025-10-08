import { FormEvent, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { APP_TITLE } from '@/config/env';
import { useAuth } from '@/context/AuthContext';

import './LoginPage.css';

export function LoginPage() {
  const { isAuthenticated, login, status, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = (location.state as { from?: Location })?.from?.pathname ?? '/';

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : 'Não foi possível autenticar';
      setLocalError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login">
      <section className="login__panel">
        <h1>{APP_TITLE}</h1>
        <p>Entre com seu usuário institucional para continuar.</p>

        <form className="login__form" onSubmit={handleSubmit}>
          <label>
            <span>E-mail</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="nome@instituicao.gov.br"
              autoComplete="email"
              required
            />
          </label>

          <label>
            <span>Senha</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </label>

          {(localError || error) && <p className="login__error">{localError ?? error}</p>}

          <button type="submit" disabled={isSubmitting || status === 'loading'}>
            {isSubmitting || status === 'loading' ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </section>

      <section className="login__aside">
        <div className="login__overlay" />
        <div className="login__aside-content">
          <h2>Cooperação em escala</h2>
          <p>
            Organize e acompanhe o trabalho dos grupos, consolide respostas, gere estudos comparados e
            publique referenciais curriculares com segurança.
          </p>
        </div>
      </section>
    </div>
  );
}
