import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { AuditLog, OnlineUser, PaginatedResponse } from '@/api/types';

interface UseAuditLogsParams {
  entidade?: string;
  entidadeId?: number;
}

export function useAuditLogs({ entidade, entidadeId }: UseAuditLogsParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['audit-logs', { entidade, entidadeId }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<AuditLog>>('/audit', {
        query: {
          entidade,
          entidade_id: entidadeId,
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

export function useOnlineUsers() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['online-users'],
    queryFn: async () => {
      const response = await client.get<OnlineUser[]>('/audit/online');
      return response.data;
    },
    refetchInterval: 60_000,
  });
}
