import { useCallback, useMemo } from 'react';

import { useAuth } from '@/context/AuthContext';

type ClienteOption = { id: number; nome: string; slug: string };

export function useAdminScope() {
  const { user, activeClienteId, setActiveCliente } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';
  const clientes = useMemo<ClienteOption[]>(
    () => (isSuperAdmin ? user?.clientes ?? [] : []),
    [isSuperAdmin, user?.clientes],
  );
  const selectedClienteId = isSuperAdmin ? activeClienteId ?? '' : '';

  const setSelectedClienteId = useCallback(
    (value: number | '') => {
      void setActiveCliente(value === '' ? null : value);
    },
    [setActiveCliente],
  );

  const headers = useMemo(() => {
    if (isSuperAdmin && selectedClienteId) {
      return { 'X-Cliente-ID': String(selectedClienteId) };
    }
    return undefined;
  }, [isSuperAdmin, selectedClienteId]);

  return {
    isSuperAdmin,
    clientes,
    selectedClienteId,
    setSelectedClienteId,
    headers,
  };
}
