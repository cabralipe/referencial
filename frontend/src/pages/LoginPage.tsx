import { FormEvent, useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/api/client';
import { APP_TITLE } from '@/config/env';
import { useAuth } from '@/context/AuthContext';
import { PageInstructions } from '@/components/common/PageInstructions';

import './LoginPage.css';

export function LoginPage() {
  const queryClient = useQueryClient();
  const { isAuthenticated, login, status, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    queryClient.clear();
  }, [queryClient]);

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

        <PageInstructions
          title="Antes de acessar"
          description="Garanta que o cadastro institucional esteja ativo para evitar bloqueios."
          items={[
            {
              title: 'E-mail corporativo',
              description: 'Utilize o endereço fornecido pela sua instituição ou equipe de projetos.',
            },
            {
              title: 'Senha atualizada',
              description: 'Caso tenha esquecido, recupere a senha no portal do servidor antes de tentar novamente.',
            },
            {
              title: 'Ambiente seguro',
              description: 'Evite redes públicas ao acessar informações sensíveis do referencial.',
            },
          ]}
        />
      </section>

      <section className="login__aside">
        <div className="login__overlay" />
        <div className="login__aside-content">
          <h2>Plataforma MEB</h2>
          <p>
            Organize e acompanhe o trabalho dos grupos, consolide respostas, gere estudos comparados e
            publique referenciais curriculares com segurança.
          </p>
        </div>
      </section>
    </div>
  );
}
