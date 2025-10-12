import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { Notificacao, PaginatedResponse } from '@/api/types';
import { useAuth } from '@/context/AuthContext';

import { useWebSocket } from './useWebSocket';

export function useNotificacoes() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['notificacoes'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Notificacao>>('/notificacoes', {
        query: {
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
    refetchInterval: 60_000,
  });
}

export function useMarcarNotificacaoLida() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificacaoId: number) => {
      const response = await client.put<Notificacao>(`/notificacoes/${notificacaoId}/lida`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificacoes'] });
    },
  });
}

export function useNotificationsRealtime(enabled = true) {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();

  const connection = useWebSocket({
    path: '/ws/notifications/',
    enabled: enabled && isAuthenticated,
    onMessage: () => {
      queryClient.invalidateQueries({ queryKey: ['notificacoes'] });
    },
  });

  return connection;
}
