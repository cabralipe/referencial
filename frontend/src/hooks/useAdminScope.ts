import { useEffect, useMemo, useState } from 'react';

import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';

type ClienteOption = { id: number; nome: string };

export function useAdminScope() {
  const { user } = useAuth();
  const client = useApiClient();
  const isSuperAdmin = user?.role === 'super_admin';
  const [clientes, setClientes] = useState<ClienteOption[]>([]);
  const [selectedClienteId, setSelectedClienteId] = useState<number | ''>(() => {
    if (typeof window === 'undefined') return '';
    const stored = window.localStorage.getItem('adminScopeClienteId');
    return stored ? Number(stored) : '';
  });

  useEffect(() => {
    if (!isSuperAdmin) return;
    let active = true;
    client
      .get<{ results: ClienteOption[] }>('/admin/clientes', { query: { page_size: 200 } })
      .then((response) => {
        if (!active) return;
        setClientes(response.data.results ?? []);
      })
      .catch(() => {
        if (!active) return;
        setClientes([]);
      });
    return () => {
      active = false;
    };
  }, [client, isSuperAdmin]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    if (typeof window === 'undefined') return;
    if (selectedClienteId) {
      window.localStorage.setItem('adminScopeClienteId', String(selectedClienteId));
    } else {
      window.localStorage.removeItem('adminScopeClienteId');
    }
  }, [isSuperAdmin, selectedClienteId]);

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
