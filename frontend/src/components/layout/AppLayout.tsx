import { CSSProperties, useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import Icon from '@/components/common/Icon';
import { MebAssistant } from '@/components/meb/MebAssistant';
import { Breadcrumbs } from '@/components/common/Breadcrumbs';
import { buildBackendUrl } from '@/config/env';

import './AppLayout.css';

type NavItem =
  | {
    label: string;
    icon: string;
    to: string;
    only?: string[];
    external?: false;
    href?: never;
  }
  | {
    label: string;
    icon: string;
    href: string;
    external: true;
    only?: string[];
    to?: never;
  };

interface AreaAtuacaoOption {
  id: number;
  nome: string;
}

interface AreaAtuacaoResponse {
  required: boolean;
  title: string;
  tipos: AreaAtuacaoOption[];
  current_tipo_cadastro_id: number | null;
}

const AREA_ATUACAO_ROLES = new Set(['diretor', 'coordenador_pedagogico', 'professor']);

export function AppLayout() {
  const { cliente, user, logout, activeClienteId, setActiveCliente } = useAuth();
  const api = useApiClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [isDesktop, setIsDesktop] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.matchMedia('(min-width: 1024px)').matches : true,
  );
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    const persisted = window.localStorage.getItem('appSidebarOpen');
    if (persisted === 'true') return true;
    if (persisted === 'false') return false;
    return window.matchMedia('(max-width: 1023px)').matches ? false : true;
  });
  const [sidebarCompact, setSidebarCompact] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem('appSidebarCompact') === 'true';
  });
  const [focusMode, setFocusMode] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem('appFocusMode') === 'true';
  });
  const [areaAtuacaoRequired, setAreaAtuacaoRequired] = useState(false);
  const [areaAtuacaoLoading, setAreaAtuacaoLoading] = useState(false);
  const [areaAtuacaoSubmitting, setAreaAtuacaoSubmitting] = useState(false);
  const [areaAtuacaoOptions, setAreaAtuacaoOptions] = useState<AreaAtuacaoOption[]>([]);
  const [selectedAreaAtuacaoId, setSelectedAreaAtuacaoId] = useState<number | ''>('');
  const [areaAtuacaoTitle, setAreaAtuacaoTitle] = useState('Qual sua área de atuação?');
  const [areaAtuacaoError, setAreaAtuacaoError] = useState<string | null>(null);
  const sidenavInnerRef = useRef<HTMLDivElement | null>(null);

  const roleLabel = useMemo(() => {
    const role = user?.role ?? '';
    const map: Record<string, string> = {
      super_admin: 'Superadmin',
      admin_cliente: 'Admin SEMED',
      diretor: 'Diretor',
      coordenador_pedagogico: 'Coordenador Pedagógico',
      articulador: 'Redação',
      revisor: 'Revisor',
      membro_gt: 'Membro GT',
      leitor: 'Leitor',
    };
    return map[role] ?? role;
  }, [user?.role]);

  const userInitials = useMemo(() => {
    const source = (user?.nome || user?.email || 'RF').trim();
    const parts = source.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase();
    }
    return (source.slice(0, 2) || 'RF').toUpperCase();
  }, [user?.email, user?.nome]);

  const themeStyles = useMemo(() => {
    const primary = cliente?.tema?.cor_primaria ?? '#2563eb';
    const secondary = cliente?.tema?.cor_secundaria ?? '#0ea5e9';
    return {
      '--app-primary': primary,
      '--app-secondary': secondary,
    } as CSSProperties;
  }, [cliente?.tema?.cor_primaria, cliente?.tema?.cor_secundaria]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  useEffect(() => {
    window.localStorage.setItem('appSidebarOpen', String(sidebarOpen));
  }, [sidebarOpen]);

  useEffect(() => {
    window.localStorage.setItem('appSidebarCompact', String(sidebarCompact));
  }, [sidebarCompact]);

  useEffect(() => {
    window.localStorage.setItem('appFocusMode', String(focusMode));
  }, [focusMode]);

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)');
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    setIsDesktop(mq.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    if (isDesktop && !sidebarOpen) setSidebarOpen(true);
  }, [isDesktop, sidebarOpen]);

  useEffect(() => {
    if (!isDesktop && sidebarCompact) setSidebarCompact(false);
  }, [isDesktop, sidebarCompact]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const focusParam = params.get('focus');
    if (focusParam === '1') {
      setFocusMode(true);
    } else if (focusParam === '0') {
      setFocusMode(false);
    }
  }, [location.search]);

  const isGtMember = user?.role === 'membro_gt';
  const isSchoolLeader = user?.role === 'diretor' || user?.role === 'coordenador_pedagogico';
  const isProfessor = user?.role === 'professor';
  const isRedator = user?.role === 'articulador';
  const isAdmin = user?.role === 'admin_cliente' || user?.role === 'super_admin';
  const avaHref = buildBackendUrl('/ava/catalogo/');

  const navItems = useMemo(() => {
    const avaNavItem = { href: avaHref, label: 'Acessar AVA', icon: 'library', external: true } as const;
    if (isGtMember) {
      return [
        { to: '/inicio', label: 'Início', icon: 'dashboard' },
        avaNavItem,
        { to: '/minha-trilha', label: 'Minha Trilha', icon: 'tasks' },
        { to: '/texto', label: 'Construção de Texto', icon: 'document' },
        { to: '/cadernos', label: 'Cadernos', icon: 'library' },
        { to: '/mural', label: 'Mural', icon: 'comment' },
        { to: '/ppp', label: 'PPP', icon: 'kanban' },
        { to: '/ajuda', label: 'Ajuda', icon: 'help' },
      ];
    }
    if (isSchoolLeader || isProfessor) {
      return [
        { to: '/inicio', label: 'Inicio', icon: 'dashboard' },
        avaNavItem,
        { to: '/ppp', label: 'PPP da Escola', icon: 'document' },
        { to: '/ajuda', label: 'Ajuda', icon: 'help' },
      ];
    }
    if (isAdmin) {
      const adminItems = [
        { to: '/admin/console', label: 'Admin Console', icon: 'settings' },
        { to: '/consultas-publicas', label: 'Consultas públicas', icon: 'document' },
        avaNavItem,
        { to: '/admin/trilhas', label: 'Admin: Trilhas', icon: 'tasks' },
        { to: '/admin/mural', label: 'Admin: Mural', icon: 'comment' },
        { to: '/admin/ppp', label: 'Admin: PPP', icon: 'document' },
      ];
      if (user?.role === 'super_admin') {
        adminItems.unshift(
          { to: '/admin/console/clientes', label: 'Clientes', icon: 'users' },
          { to: '/admin/console/clientes-config', label: 'Configuração do cliente', icon: 'settings' },
        );
      }
      return adminItems;
    }
    if (isRedator) {
      return [
        { to: '/redator/painel', label: 'Painel', icon: 'dashboard' },
        avaNavItem,
        { to: '/ppp', label: 'PPP da Escola', icon: 'document' },
        { to: '/redator/revisoes', label: 'Revisões', icon: 'review' },
        { to: '/redator/conteudos', label: 'Conteúdos', icon: 'library' },
        { to: '/redator/mural', label: 'Mural', icon: 'comment' },
        { to: '/redator/exportacoes', label: 'Exportações', icon: 'export' },
      ];
    }
    return [
      { to: '/', label: 'Painel', icon: 'dashboard' },
      { to: '/tarefas', label: 'Trilhas pedagógicas', icon: 'tasks' },
      { to: '/texto-unico', label: 'Texto único', icon: 'document' },
      { to: '/quadros', label: 'Quadros', icon: 'kanban' },
      { to: '/formularios', label: 'Formulários', icon: 'form' },
      { to: '/revisoes', label: 'Revisões', icon: 'review' },
      { to: '/pareceres', label: 'Pareceres', icon: 'review', only: ['membro_gt', 'articulador'] },
      { to: '/comentarios', label: 'Comentários', icon: 'comment' },
      { to: '/relatorios', label: 'Relatórios', icon: 'document', only: ['admin_cliente', 'super_admin'] },
      { to: '/biblioteca', label: 'Referências', icon: 'library' },
      avaNavItem,
      { to: '/exportacoes', label: 'Exportações', icon: 'export' },
      { to: '/diff', label: 'Diff', icon: 'diff' },
      { to: '/auditoria', label: 'Auditoria', icon: 'audit' },
      { to: '/bloqueios', label: 'Bloqueios', icon: 'audit', only: ['admin_cliente', 'super_admin'] },
      { to: '/gamificacao', label: 'Gamificação', icon: 'tasks', only: ['admin_cliente', 'super_admin'] },
    ];
  }, [avaHref, isAdmin, isGtMember, isProfessor, isRedator, isSchoolLeader, user?.role]);

  const selectedCliente = useMemo(() => {
    if (!activeClienteId) return null;
    return (user?.clientes ?? []).find((item) => item.id === activeClienteId) ?? null;
  }, [activeClienteId, user?.clientes]);
  const canSwitchCliente = useMemo(
    () => (user?.clientes ?? []).length > 1 || user?.role === 'super_admin',
    [user?.clientes, user?.role],
  );

  const shouldCheckAreaAtuacao = Boolean(
    user?.id && user?.clienteId && AREA_ATUACAO_ROLES.has(user.role),
  );

  useEffect(() => {
    if (!shouldCheckAreaAtuacao) {
      setAreaAtuacaoRequired(false);
      setAreaAtuacaoLoading(false);
      setAreaAtuacaoSubmitting(false);
      setAreaAtuacaoOptions([]);
      setSelectedAreaAtuacaoId('');
      setAreaAtuacaoError(null);
      setAreaAtuacaoTitle('Qual sua área de atuação?');
      return;
    }

    let cancelled = false;
    setAreaAtuacaoLoading(true);
    setAreaAtuacaoError(null);

    api
      .get<AreaAtuacaoResponse>('auth/area-atuacao')
      .then(({ data }) => {
        if (cancelled) return;
        setAreaAtuacaoRequired(Boolean(data.required));
        setAreaAtuacaoTitle(data.title || 'Qual sua área de atuação?');
        setAreaAtuacaoOptions(data.tipos || []);
        setSelectedAreaAtuacaoId(data.current_tipo_cadastro_id ?? '');
      })
      .catch((error) => {
        if (cancelled) return;
        setAreaAtuacaoRequired(true);
        setAreaAtuacaoOptions([]);
        setAreaAtuacaoError(error instanceof Error ? error.message : 'Não foi possível carregar os tipos de usuário.');
      })
      .finally(() => {
        if (!cancelled) {
          setAreaAtuacaoLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, shouldCheckAreaAtuacao, user?.id, user?.clienteId, user?.role]);

  const handleConfirmarAreaAtuacao = async () => {
    if (!selectedAreaAtuacaoId) {
      setAreaAtuacaoError('Selecione uma opção para continuar.');
      return;
    }
    setAreaAtuacaoSubmitting(true);
    setAreaAtuacaoError(null);
    try {
      await api.post('auth/area-atuacao', {
        body: { tipo_cadastro_id: selectedAreaAtuacaoId },
      });
      window.location.reload();
    } catch (error) {
      setAreaAtuacaoSubmitting(false);
      setAreaAtuacaoError(error instanceof Error ? error.message : 'Não foi possível salvar sua área de atuação.');
    }
  };

  const showAreaAtuacaoModal = shouldCheckAreaAtuacao && (areaAtuacaoLoading || areaAtuacaoRequired);

  return (
    <div
      className={`app-shell ${isGtMember ? 'app-shell--gt' : ''} ${focusMode ? 'app-shell--focus' : ''} ${sidebarOpen ? 'app-shell--sidebar-open' : 'app-shell--sidebar-closed'} ${isDesktop && sidebarCompact ? 'app-shell--sidebar-compact' : ''}`}
      style={themeStyles}
    >
      <aside
        id="app-sidenav"
        className={`app-shell__sidenav ${sidebarOpen ? 'is-open' : 'is-closed'}`}
        role="navigation"
        aria-label="Menu principal"
        aria-hidden={!sidebarOpen}
      >
        <div className="app-shell__sidenav-inner" ref={sidenavInnerRef} tabIndex={0}>
          <div className="app-shell__brand">
            {cliente?.tema?.logo_url ? (
              <img src={cliente.tema.logo_url} alt={cliente.cliente.nome} />
            ) : (
              <div className="app-shell__logo-fallback">{cliente?.cliente?.nome?.slice(0, 1) ?? 'R'}</div>
            )}
            <div className="app-shell__brand-text">
              <strong>{cliente?.cliente?.nome ?? 'Referencial Curricular'}</strong>
            </div>
          </div>

          {sidebarCompact ? (
            <div className="app-shell__user-block--compact">
              <button
                type="button"
                className="app-shell__collapse-btn"
                aria-label={sidebarCompact ? 'Expandir menu' : 'Recolher menu'}
                onClick={() => setSidebarCompact((v) => !v)}
              >
                <Icon name="chevron-right" className="menu__icon" ariaHidden />
              </button>
            </div>
          ) : (
            <div className="app-shell__user-block">
              <div className="app-shell__user-info">
                <span>{user?.nome ?? user?.email}</span>
                <small>{roleLabel}</small>
              </div>
              <button
                type="button"
                className="app-shell__collapse-btn"
                aria-label={sidebarCompact ? 'Expandir menu' : 'Recolher menu'}
                onClick={() => setSidebarCompact((v) => !v)}
              >
                <Icon name="chevron-left" className="menu__icon" ariaHidden />
              </button>
            </div>
          )}

          <nav className="app-shell__nav-vertical">
            {navItems.map((item) => {
              if (item.only && !item.only.includes(user?.role ?? '')) {
                return null;
              }
              if (item.external) {
                return (
                  <a key={item.label} href={item.href} target="_blank" rel="noopener noreferrer">
                    <Icon name={item.icon} className="menu__icon" ariaHidden />
                    <span className="menu__label">{item.label}</span>
                  </a>
                );
              }
              return (
                <NavLink key={item.to} to={item.to!} end={item.to === '/'}>
                  <Icon name={item.icon} className="menu__icon" ariaHidden />
                  <span className="menu__label">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      </aside>

      <div
        className={`app-shell__overlay ${sidebarOpen ? 'is-visible' : ''}`}
        aria-hidden={!sidebarOpen}
        onClick={() => {
          if (!isDesktop) setSidebarOpen(false);
        }}
      />

      <header className="app-shell__header">
        <button
          type="button"
          className="app-shell__toggle"
          aria-label="Abrir/fechar menu"
          onClick={() => setSidebarOpen((v) => !v)}
        >
          <span className="toggle__bars" aria-hidden="true" />
        </button>

        <div className="app-shell__brand app-shell__brand--header">
          {cliente?.tema?.logo_url ? (
            <img src={cliente.tema.logo_url} alt={cliente.cliente.nome} />
          ) : (
            <div className="app-shell__logo-fallback">{cliente?.cliente?.nome?.slice(0, 1) ?? 'R'}</div>
          )}
          <div className="app-shell__brand-text">
            <strong>{cliente?.cliente?.nome ?? 'Referencial Curricular'}</strong>
          </div>
        </div>

        {user?.role === 'super_admin' && selectedCliente && (
          <div className="app-shell__client-context">
            <span>Cliente selecionado:</span>
            <strong>{selectedCliente.nome}</strong>
          </div>
        )}

        <div className="app-shell__header-search">
          <Icon name="search" className="menu__icon" ariaHidden />
          <input type="search" placeholder="Buscar recursos..." aria-label="Buscar recursos" />
        </div>

        <div className="app-shell__user">
          <button type="button" className="app-shell__notify" aria-label="Notificações">
            <Icon name="notifications" className="menu__icon" ariaHidden />
            <span className="app-shell__notify-dot" />
          </button>
          <div className="app-shell__user-meta">
            <strong>{user?.nome ?? 'Usuário'}</strong>
            <small>{roleLabel}</small>
            {canSwitchCliente && (
              <label className="app-shell__client-switch">
                <span>Cliente</span>
                <select
                  value={activeClienteId ?? ''}
                  onChange={(event) => {
                    const value = event.target.value ? Number(event.target.value) : null;
                    void setActiveCliente(value);
                  }}
                >
                  {user?.role === 'super_admin' && <option value="">Todos</option>}
                  {(user?.clientes ?? []).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <div className="app-shell__avatar" aria-hidden="true">
            {userInitials}
          </div>
          <button type="button" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      <main className="app-shell__main">
        <div className="app-shell__content">
          <Breadcrumbs />
          <Outlet />
        </div>
      </main>

      {cliente?.tema?.rodape_html && (
        <footer className="app-shell__footer" dangerouslySetInnerHTML={{ __html: cliente.tema.rodape_html }} />
      )}

      <MebAssistant />

      {showAreaAtuacaoModal && (
        <div className="app-shell__modal-overlay" role="dialog" aria-modal="true" aria-labelledby="area-atuacao-title">
          <div className="app-shell__modal" onClick={(event) => event.stopPropagation()}>
            <header className="app-shell__modal-header">
              <p className="app-shell__modal-eyebrow">Cadastro complementar</p>
              <h2 id="area-atuacao-title">{areaAtuacaoTitle}</h2>
              <p>Selecione o tipo de usuário que representa sua atuação atual. Essa confirmação é obrigatória.</p>
            </header>

            {areaAtuacaoLoading ? (
              <div className="app-shell__modal-state">Carregando opções...</div>
            ) : (
              <>
                <div className="app-shell__modal-options">
                  {areaAtuacaoOptions.map((option) => (
                    <label
                      key={option.id}
                      className={`app-shell__modal-option ${selectedAreaAtuacaoId === option.id ? 'is-selected' : ''}`}
                    >
                      <input
                        type="radio"
                        name="area_atuacao"
                        value={option.id}
                        checked={selectedAreaAtuacaoId === option.id}
                        onChange={() => setSelectedAreaAtuacaoId(option.id)}
                        disabled={areaAtuacaoSubmitting}
                      />
                      <span>{option.nome}</span>
                    </label>
                  ))}
                </div>

                {!areaAtuacaoOptions.length && (
                  <div className="app-shell__modal-state">
                    Nenhum tipo de usuário ativo foi encontrado para este município.
                  </div>
                )}

                {areaAtuacaoError && <div className="app-shell__modal-error">{areaAtuacaoError}</div>}

                <div className="app-shell__modal-actions">
                  <button
                    type="button"
                    className="app-shell__modal-button"
                    onClick={handleConfirmarAreaAtuacao}
                    disabled={areaAtuacaoSubmitting || areaAtuacaoLoading || !areaAtuacaoOptions.length}
                  >
                    {areaAtuacaoSubmitting ? 'Confirmando...' : 'Confirmar'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
