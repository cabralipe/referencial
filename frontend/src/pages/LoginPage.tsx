import { FormEvent, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/api/client';
import { useAuth } from '@/context/AuthContext';

// Remove import './LoginPage.css'; since we use Tailwind now

export function LoginPage() {
  const queryClient = useQueryClient();
  const { isAuthenticated, login, status, error, user } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    queryClient.clear();
  }, [queryClient]);

  const requestedPath = (location.state as { from?: Location })?.from?.pathname;

  const resolveDefaultRoute = (role?: string | null) => {
    if (role === 'diretor' || role === 'coordenador_pedagogico' || role === 'professor') {
      return '/inicio';
    }
    return '/';
  };

  const redirectTo = requestedPath ?? resolveDefaultRoute(user?.role);

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
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
    <div className="bg-slate-50 font-display text-slate-900 antialiased overflow-x-hidden selection:bg-primary selection:text-white">
      <div className="relative flex flex-col lg:flex-row min-h-screen w-full">
        {/* Desktop Left Side */}
        <div
          className="hidden lg:flex relative w-3/5 bg-gradient-to-br from-blue-600 via-primary to-cyan-400 overflow-hidden items-center justify-center p-12"
          data-alt="Abstract vibrant mesh gradient background in blue and cyan shades"
        >
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
          <div className="absolute top-20 right-20 w-96 h-96 bg-cyan-300 rounded-full blur-[100px] opacity-30 mix-blend-screen animate-pulse"></div>
          <div className="absolute bottom-20 left-20 w-96 h-96 bg-blue-500 rounded-full blur-[100px] opacity-40 mix-blend-screen"></div>

          <div className="relative z-10 flex flex-col items-start max-w-lg">
            <div className="mb-8 transform transition-transform hover:scale-105 duration-300 inline-block h-40 overflow-visible flex items-center justify-center">
              <img src={`${import.meta.env.BASE_URL}LOGO_PROLUC.png`} alt="PROLUC Logo" className="h-full w-auto object-contain drop-shadow-xl" />
            </div>
            <p className="text-blue-50 text-xl font-medium opacity-90 leading-relaxed mb-8">
              Gestão curricular integrada para um futuro educacional moderno e conectado.
            </p>
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-3xl p-6 mt-4 w-full">
              <div className="flex items-center gap-4 mb-4">
                <div className="h-3 w-3 rounded-full bg-cyan-300"></div>
                <div className="h-3 w-3 rounded-full bg-blue-300"></div>
                <div className="h-2 w-32 bg-white/20 rounded-full"></div>
              </div>
              <div className="h-32 bg-gradient-to-r from-white/10 to-transparent rounded-xl w-full flex items-center justify-center">
                <span className="material-symbols-outlined text-white/40 text-6xl">analytics</span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Top Header */}
        <div
          className="lg:hidden relative w-full h-[45vh] bg-gradient-to-br from-blue-600 via-primary to-cyan-400 rounded-b-[3rem] overflow-hidden shrink-0 shadow-lg border-b border-white/10"
          data-alt="Abstract vibrant mesh gradient background in blue and cyan shades"
        >
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-300 rounded-full blur-[80px] opacity-30 mix-blend-screen"></div>
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500 rounded-full blur-[80px] opacity-40 mix-blend-screen"></div>
          <div className="relative z-10 flex flex-col items-center justify-center h-full px-6 pb-12 text-center">
            <div className="mb-6 transform transition-transform hover:scale-105 duration-300 h-20 overflow-visible flex items-center justify-center">
              <img src={`${import.meta.env.BASE_URL}LOGO_PROLUC.png`} alt="PROLUC Logo" className="h-full w-auto object-contain drop-shadow-lg" />
            </div>
            <p className="text-blue-50 text-base font-medium opacity-95 max-w-xs leading-relaxed">
              Gestão curricular integrada para um futuro educacional moderno.
            </p>
          </div>
        </div>

        {/* Form Section */}
        <div className="w-full lg:w-2/5 flex flex-col items-center justify-start relative z-20 px-4 lg:px-12 -mt-20 lg:mt-0 pb-8 lg:pb-0 lg:bg-white lg:shadow-none lg:h-screen lg:overflow-y-auto">
          {/* Desktop Top Strip */}
          <div className="w-full max-w-md flex flex-col lg:my-auto lg:py-12">

            {/* The Card Container - styles vary for mobile/desktop */}
            <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden flex flex-col lg:bg-transparent lg:rounded-none lg:shadow-none lg:border-none lg:overflow-visible">

              <div className="pt-8 pb-2 px-8 text-center lg:p-0 lg:mb-10 lg:text-left">

                {/* Mobile-only branding in form */}
                <div className="flex items-center gap-3 hidden mb-6">
                </div>

                <h2 className="text-2xl lg:text-3xl font-bold text-slate-800 lg:text-slate-900 tracking-tight">Bem-vindo</h2>
                <p className="text-slate-500 text-sm lg:text-base mt-1 lg:mt-2">
                  {/* Text varies slightly in templates. Mobile: "Acesse com suas credenciais seguras." Desktop: "Acesse a plataforma com suas credenciais institucionais." */}
                  <span className="lg:hidden">Acesse com suas credenciais seguras.</span>
                  <span className="hidden lg:inline">Acesse a plataforma com suas credenciais institucionais.</span>
                </p>
              </div>

              <div className="p-8 pt-6 space-y-5 lg:p-0 lg:space-y-6">
                <form className="space-y-6" onSubmit={handleSubmit}>
                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-slate-700 ml-1">E-mail</label>
                    <div className="relative group">
                      <input
                        className="w-full h-14 pl-12 pr-4 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                        placeholder="nome@instituicao.com.br"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                      />
                      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors">
                        <span className="material-symbols-outlined">mail</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-center ml-1">
                      <label className="block text-sm font-semibold text-slate-700">Senha</label>
                      <a className="text-xs font-semibold text-primary hover:text-blue-700 transition-colors" href="#">Esqueceu a senha?</a>
                    </div>
                    <div className="relative group">
                      <input
                        className="w-full h-14 pl-12 pr-12 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                        placeholder="••••••••"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        autoComplete="current-password"
                      />
                      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors">
                        <span className="material-symbols-outlined">lock</span>
                      </div>
                      <button
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        <span className="material-symbols-outlined text-[20px]">{showPassword ? 'visibility' : 'visibility_off'}</span>
                      </button>
                    </div>
                  </div>

                  {(localError || error) && (
                    <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                      {localError ?? error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmitting || status === 'loading'}
                    className="w-full h-14 bg-primary hover:bg-blue-700 lg:bg-primary lg:hover:bg-blue-700 group-hover:bg-blue-700 text-white font-bold text-lg rounded-xl shadow-lg shadow-blue-500/20 transform transition-all active:scale-[0.98] flex items-center justify-center gap-2 group mt-4 bg-gradient-to-r from-primary to-blue-600 lg:bg-none"
                  >
                    {isSubmitting || status === 'loading' ? 'Entrando...' : 'Entrar'}
                    <span className="material-symbols-outlined text-white group-hover:translate-x-1 transition-transform">arrow_forward</span>
                  </button>
                </form>
              </div>

              {/* Security Badges Grid */}
              <div className="bg-slate-50 p-6 border-t border-slate-100 lg:bg-transparent lg:p-0 lg:pt-8 lg:mt-10 lg:border-t lg:border-slate-100">
                <div className="grid grid-cols-3 divide-x divide-slate-200">
                  <div className="flex flex-col items-center text-center px-1 gap-2 group cursor-default">
                    <span className="material-symbols-outlined text-primary text-[24px] group-hover:scale-110 transition-transform">badge</span>
                    <span className="text-[11px] font-semibold text-slate-600 leading-tight">E-mail<br />corporativo</span>
                  </div>
                  <div className="flex flex-col items-center text-center px-1 gap-2 group cursor-default">
                    <span className="material-symbols-outlined text-primary text-[24px] group-hover:scale-110 transition-transform">encrypted</span>
                    <span className="text-[11px] font-semibold text-slate-600 leading-tight">Senha<br />atualizada</span>
                  </div>
                  <div className="flex flex-col items-center text-center px-1 gap-2 group cursor-default">
                    <span className="material-symbols-outlined text-primary text-[24px] group-hover:scale-110 transition-transform">gpp_good</span>
                    <span className="text-[11px] font-semibold text-slate-600 leading-tight">Ambiente<br />seguro</span>
                  </div>
                </div>
              </div>

            </div>

            {/* Footer Links - Outside Card for Mobile, Inside 'w-full max-w-md' for Desktop */}
            <div className="mt-8 flex gap-6 text-sm font-medium text-slate-500 justify-center lg:mt-auto lg:pt-8 lg:gap-8 lg:text-slate-400">
              <a className="hover:text-slate-700 lg:hover:text-slate-600 transition-colors" href="#">Ajuda</a>
              <a className="hover:text-slate-700 lg:hover:text-slate-600 transition-colors" href="#">Privacidade</a>
              <a className="hover:text-slate-700 lg:hover:text-slate-600 transition-colors" href="#">Termos</a>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
