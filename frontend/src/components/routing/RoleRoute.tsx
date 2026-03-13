import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '@/context/AuthContext';

interface RoleRouteProps {
  allowed: string[];
  children: JSX.Element;
}

export function RoleRoute({ allowed, children }: RoleRouteProps) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const memberAliasRoles = new Set(['professor', 'diretor', 'coordenador_pedagogico']);
  const effectiveRole = memberAliasRoles.has(user.role) ? 'membro_gt' : user.role;

  if (!allowed.includes(effectiveRole) && !allowed.includes(user.role)) {
    const fallback =
      user.role === 'diretor' || user.role === 'coordenador_pedagogico'
        ? '/ppp'
        : effectiveRole === 'membro_gt'
        ? '/inicio'
        : effectiveRole === 'revisor'
          ? '/revisor/inbox'
          : effectiveRole === 'articulador'
            ? '/redator/revisoes'
            : '/';
    return <Navigate to={fallback} replace state={{ from: location }} />;
  }

  return children;
}
