import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '@/context/AuthContext';

import { FullPageLoader } from '../common/FullPageLoader';

interface ProtectedRouteProps {
  children: JSX.Element;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <FullPageLoader message="Restaurando sessão..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
