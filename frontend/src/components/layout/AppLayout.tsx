import { CSSProperties, useMemo } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useAuth } from '@/context/AuthContext';

import './AppLayout.css';

export function AppLayout() {
  const { cliente, user, logout } = useAuth();
  const navigate = useNavigate();

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

  return (
    <div className="app-shell" style={themeStyles}>
      <header className="app-shell__header">
        <div className="app-shell__brand">
          {cliente?.tema?.logo_url ? (
            <img src={cliente.tema.logo_url} alt={cliente.cliente.nome} />
          ) : (
            <div className="app-shell__logo-fallback">
              {cliente?.cliente?.nome?.slice(0, 1) ?? 'R'}
            </div>
          )}
          <div>
            <strong>{cliente?.cliente?.nome ?? 'Referencial Curricular'}</strong>
            {cliente?.cliente?.slug && <span>{cliente.cliente.slug}</span>}
          </div>
        </div>

        <nav className="app-shell__nav">
          <NavLink to="/" end>
            Painel
          </NavLink>
          <NavLink to="/tarefas">
            Tarefas
          </NavLink>
          <NavLink to="/texto-unico">
            Texto único
          </NavLink>
          <NavLink to="/quadros">
            Quadros
          </NavLink>
          <NavLink to="/formularios">
            Formulários
          </NavLink>
          <NavLink to="/revisoes">
            Revisões
          </NavLink>
          <NavLink to="/comentarios">
            Comentários
          </NavLink>
          <NavLink to="/notificacoes">
            Notificações
          </NavLink>
          <NavLink to="/biblioteca">
            Biblioteca
          </NavLink>
          <NavLink to="/exportacoes">
            Exportações
          </NavLink>
          <NavLink to="/diff">
            Diff
          </NavLink>
          <NavLink to="/auditoria">
            Auditoria
          </NavLink>
        </nav>

        <div className="app-shell__user">
          <div className="app-shell__user-info">
            <span>{user?.nome ?? user?.email}</span>
            <small>{user?.role}</small>
          </div>
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
    </div>
  );
}
