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

  if (!allowed.includes(user.role)) {
    const fallback =
      user.role === 'membro_gt'
        ? '/inicio'
        : user.role === 'revisor'
          ? '/revisor/inbox'
          : user.role === 'articulador'
            ? '/redator/revisoes'
            : '/';
    return <Navigate to={fallback} replace state={{ from: location }} />;
  }

  return children;
}
