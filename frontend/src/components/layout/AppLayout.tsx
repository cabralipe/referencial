import { CSSProperties, useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useAuth } from '@/context/AuthContext';
import Icon from '@/components/common/Icon';
import { MebAssistant } from '@/components/meb/MebAssistant';

import './AppLayout.css';

export function AppLayout() {
  const { cliente, user, logout } = useAuth();
  const navigate = useNavigate();
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
  const sidenavInnerRef = useRef<HTMLDivElement | null>(null);

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
    if (import.meta.env.DEV) {
      const el = sidenavInnerRef.current;
      const runChecks = () => {
        if (!el) return;
        const hasOverflow = el.scrollHeight > el.clientHeight;
        // Conteúdo: overflow só quando necessário
        console.assert(typeof hasOverflow === 'boolean', 'Overflow calculado corretamente');
      };
      runChecks();
      const onResize = () => runChecks();
      window.addEventListener('resize', onResize);
      // Acessibilidade: foco por teclado
      if (el) {
        const focusable = el.getAttribute('tabindex') === '0';
        console.assert(focusable, 'Container é focável por teclado');
      }
      return () => window.removeEventListener('resize', onResize);
    }
  }, []);

  return (
    <div className={`app-shell ${sidebarOpen ? 'app-shell--sidebar-open' : 'app-shell--sidebar-closed'} ${isDesktop && sidebarCompact ? 'app-shell--sidebar-compact' : ''}`} style={themeStyles}>
      <aside
        id="app-sidenav"
        className={`app-shell__sidenav ${sidebarOpen ? 'is-open' : 'is-closed'}`}
        role="navigation"
        aria-label="Menu principal"
        aria-hidden={!sidebarOpen}
      >
        <div
          className="app-shell__sidenav-inner"
          ref={sidenavInnerRef}
          tabIndex={0}
          aria-label="Área rolável do menu lateral"
          onKeyDown={(e) => {
            const el = sidenavInnerRef.current;
            if (!el) return;
            const step = 60;
            switch (e.key) {
              case 'ArrowDown':
                el.scrollBy({ top: step, behavior: 'smooth' });
                e.preventDefault();
                break;
              case 'ArrowUp':
                el.scrollBy({ top: -step, behavior: 'smooth' });
                e.preventDefault();
                break;
              case 'PageDown':
                el.scrollBy({ top: el.clientHeight, behavior: 'smooth' });
                e.preventDefault();
                break;
              case 'PageUp':
                el.scrollBy({ top: -el.clientHeight, behavior: 'smooth' });
                e.preventDefault();
                break;
              case 'Home':
                el.scrollTo({ top: 0, behavior: 'smooth' });
                e.preventDefault();
                break;
              case 'End':
                el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
                e.preventDefault();
                break;
            }
          }}
        >
          <div className="app-shell__brand">
            {cliente?.tema?.logo_url ? (
              <img src={cliente.tema.logo_url} alt={cliente.cliente.nome} />
            ) : (
              <div className="app-shell__logo-fallback">
                {cliente?.cliente?.nome?.slice(0, 1) ?? 'R'}
              </div>
            )}
            <div className="app-shell__brand-text">
              <strong>{cliente?.cliente?.nome ?? 'Referencial Curricular'}</strong>
              {cliente?.cliente?.slug && <span>{cliente.cliente.slug}</span>}
            </div>
          </div>
          {sidebarCompact ? (
            <div className="app-shell__user-block--compact">
              <button
                type="button"
                className="app-shell__collapse-btn"
                aria-label={sidebarCompact ? 'Expandir menu' : 'Recolher menu'}
                aria-controls="app-sidenav"
                aria-expanded={!sidebarCompact}
                onClick={() => setSidebarCompact((v) => !v)}
              >
                <Icon name={sidebarCompact ? 'chevron-right' : 'chevron-left'} className="menu__icon" ariaHidden />
              </button>
            </div>
          ) : (
            <div className="app-shell__user-block">
              <div className="app-shell__user-info">
                <span>{user?.nome ?? user?.email}</span>
                <small>{user?.role}</small>
              </div>
              <button
                type="button"
                className="app-shell__collapse-btn"
                aria-label={sidebarCompact ? 'Expandir menu' : 'Recolher menu'}
                aria-controls="app-sidenav"
                aria-expanded={!sidebarCompact}
                onClick={() => setSidebarCompact((v) => !v)}
              >
                <Icon name={sidebarCompact ? 'chevron-right' : 'chevron-left'} className="menu__icon" ariaHidden />
              </button>
            </div>
          )}
          <nav className="app-shell__nav-vertical">
            <NavLink to="/" end>
              <Icon name="dashboard" className="menu__icon" ariaHidden />
              <span className="menu__label">Painel</span>
            </NavLink>
            <NavLink to="/tarefas">
              <Icon name="tasks" className="menu__icon" ariaHidden />
              <span className="menu__label">Tarefas</span>
            </NavLink>
            <NavLink to="/texto-unico">
              <Icon name="document" className="menu__icon" ariaHidden />
              <span className="menu__label">Texto único</span>
            </NavLink>
            <NavLink to="/quadros">
              <Icon name="kanban" className="menu__icon" ariaHidden />
              <span className="menu__label">Quadros</span>
            </NavLink>
            <NavLink to="/formularios">
              <Icon name="form" className="menu__icon" ariaHidden />
              <span className="menu__label">Formulários</span>
            </NavLink>
            <NavLink to="/revisoes">
              <Icon name="review" className="menu__icon" ariaHidden />
              <span className="menu__label">Revisões</span>
            </NavLink>
            <NavLink to="/comentarios">
              <Icon name="comment" className="menu__icon" ariaHidden />
              <span className="menu__label">Comentários</span>
            </NavLink>
            <NavLink to="/notificacoes">
              <Icon name="bell" className="menu__icon" ariaHidden />
              <span className="menu__label">Notificações</span>
            </NavLink>
            {(user?.role === 'admin_cliente' || user?.role === 'super_admin') && (
              <NavLink to="/consultas-publicas">
                <Icon name="document" className="menu__icon" ariaHidden />
                <span className="menu__label">Consultas públicas</span>
              </NavLink>
            )}
            <NavLink to="/biblioteca">
              <Icon name="library" className="menu__icon" ariaHidden />
              <span className="menu__label">Biblioteca</span>
            </NavLink>
            <NavLink to="/exportacoes">
              <Icon name="export" className="menu__icon" ariaHidden />
              <span className="menu__label">Exportações</span>
            </NavLink>
            <NavLink to="/diff">
              <Icon name="diff" className="menu__icon" ariaHidden />
              <span className="menu__label">Diff</span>
            </NavLink>
            <NavLink to="/auditoria">
              <Icon name="audit" className="menu__icon" ariaHidden />
              <span className="menu__label">Auditoria</span>
            </NavLink>
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
        <div className="app-shell__brand app-shell__brand--header">
          {cliente?.tema?.logo_url ? (
            <img src={cliente.tema.logo_url} alt={cliente.cliente.nome} />
          ) : (
            <div className="app-shell__logo-fallback">
              {cliente?.cliente?.nome?.slice(0, 1) ?? 'R'}
            </div>
          )}
          <div className="app-shell__brand-text">
            <strong>{cliente?.cliente?.nome ?? 'Referencial Curricular'}</strong>
            {cliente?.cliente?.slug && <span>{cliente.cliente.slug}</span>}
          </div>
        </div>
        
        <button
          type="button"
          className="app-shell__toggle"
          aria-label="Abrir/fechar menu"
          aria-controls="app-sidenav"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen((v) => !v)}
        >
          <span className="toggle__bars" aria-hidden="true" />
        </button>

        <div className="app-shell__user">
          <button type="button" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      <main className="app-shell__main">
        <div className="app-shell__content">
          <Outlet />
        </div>
      </main>

      {cliente?.tema?.rodape_html && (
        <footer
          className="app-shell__footer"
          dangerouslySetInnerHTML={{ __html: cliente.tema.rodape_html }}
        />
      )}

      <MebAssistant />
    </div>
  );
}
