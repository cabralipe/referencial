import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { Pergunta } from '@/api/types';

export function usePerguntas(tarefaId?: string | number) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(tarefaId),
    queryKey: ['tarefas', tarefaId, 'perguntas'],
    queryFn: async () => {
      const response = await client.get<Pergunta[]>(`/tarefas/${tarefaId}/perguntas`);
      return response.data;
    },
  });
}
