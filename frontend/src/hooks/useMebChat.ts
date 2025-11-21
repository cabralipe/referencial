import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { MebMessage, MebThread } from '@/api/types';

type EnabledOption = {
  enabled?: boolean;
};

export function useMebThreadMe({ enabled = true }: EnabledOption = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['meb', 'thread', 'me'],
    enabled,
    queryFn: async () => {
      const response = await client.get<MebThread>('/meb/threads/me');
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function useMebThreads({ enabled = true }: EnabledOption = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['meb', 'threads'],
    enabled,
    queryFn: async () => {
      const response = await client.get<MebThread[]>('/meb/threads');
      return response.data;
    },
    refetchInterval: 30_000,
  });
}

type UseMebMessagesOptions = {
  usuarioId?: number | null;
  enabled?: boolean;
};

export function useMebMessages({ usuarioId, enabled = true }: UseMebMessagesOptions) {
  const client = useApiClient();
  const key = usuarioId ?? 'me';

  return useQuery({
    queryKey: ['meb', 'messages', key],
    enabled,
    queryFn: async () => {
      const response = await client.get<MebMessage[]>('/meb/mensagens', {
        query: usuarioId ? { usuario_id: usuarioId } : undefined,
      });
      return response.data;
    },
    refetchInterval: 12_000,
  });
}

type SendMessageVariables = {
  conteudo: string;
  usuarioId?: number | null;
};

type BroadcastMessageVariables = {
  conteudo: string;
  alvo: 'usuario' | 'gt' | 'cliente';
  usuarioId?: number | null;
  gtIds?: number[];
};

export function useSendMebMessage() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ conteudo, usuarioId }: SendMessageVariables) => {
      const payload: Record<string, unknown> = { conteudo };
      if (usuarioId) {
        payload.usuario = usuarioId;
      }
      const response = await client.post<MebMessage>('/meb/mensagens', {
        body: payload,
      });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      const key = variables?.usuarioId ?? 'me';
      queryClient.invalidateQueries({ queryKey: ['meb', 'messages', key] });
      queryClient.invalidateQueries({ queryKey: ['meb', 'threads'] });
      queryClient.invalidateQueries({ queryKey: ['meb', 'thread', 'me'] });
    },
  });
}

export function useBroadcastMebMessage() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ conteudo, alvo, usuarioId, gtIds }: BroadcastMessageVariables) => {
      const body: Record<string, unknown> = {
        conteudo,
        alcance: alvo,
      };
      if (alvo === 'usuario' && usuarioId) {
        body.usuario_ids = [usuarioId];
      }
      if (alvo === 'gt' && gtIds && gtIds.length > 0) {
        body.gt_ids = gtIds;
      }
      const response = await client.post<{ sent: number }>('/meb/mensagens/broadcast', {
        body,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meb', 'messages'] });
      queryClient.invalidateQueries({ queryKey: ['meb', 'threads'] });
      queryClient.invalidateQueries({ queryKey: ['meb', 'thread', 'me'] });
    },
  });
}

export function useUploadMebAvatar() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('avatar', file);
      const response = await client.post<{ url: string }>('/meb/avatar', {
        body: formData,
      });
      return response.data;
    },
  });
}
