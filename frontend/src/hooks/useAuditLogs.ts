import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { AuditLog, OnlineUser, PaginatedResponse } from '@/api/types';

interface UseAuditLogsParams {
  entidade?: string;
  entidadeId?: number;
  usuarioId?: number;
  acao?: 'created' | 'updated' | 'deleted' | string;
  dateFrom?: string; // ISO date or datetime
  dateTo?: string;   // ISO date or datetime
  pageSize?: number;
  enabled?: boolean;
}

export function useAuditLogs({ entidade, entidadeId, usuarioId, acao, dateFrom, dateTo, pageSize, enabled }: UseAuditLogsParams = {}) {
  const client = useApiClient();

  return useQuery({
    enabled: enabled ?? (entidade ? Boolean(entidadeId) : true),
    queryKey: ['audit-logs', { entidade, entidadeId, usuarioId, acao, dateFrom, dateTo, pageSize }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<AuditLog>>('/audit', {
        query: {
          entidade,
          entidade_id: entidadeId,
          usuario_id: usuarioId,
          acao,
          date_from: dateFrom,
          date_to: dateTo,
          page_size: pageSize ?? 200,
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

interface UseSessionHistoryParams {
  days?: number;
  limit?: number;
}

export function useSessionHistory({ days = 30, limit = 100 }: UseSessionHistoryParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['session-history', { days, limit }],
    queryFn: async () => {
      const response = await client.get<OnlineUser[]>('/audit/sessions', {
        query: { days, limit },
      });
      return response.data;
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}
