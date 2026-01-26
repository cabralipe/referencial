import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { Resposta } from '@/api/types';

export function useResposta(respostaId?: number | string | null) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(respostaId),
    queryKey: ['respostas', 'detail', respostaId],
    queryFn: async () => {
      const response = await client.get<Resposta>(`/respostas/${respostaId}`);
      return response.data;
    },
  });
}

interface UpdateRespostaInput {
  respostaId: number;
  gt: number;
  pergunta: number;
  conteudo_html: string;
  etag?: string;
}

export function useUpdateResposta() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ respostaId, gt, pergunta, conteudo_html, etag }: UpdateRespostaInput) => {
      const response = await client.put<Resposta>(`/respostas/${respostaId}`, {
        body: {
          gt,
          pergunta,
          conteudo_html,
        },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['respostas', data.gt] });
      queryClient.invalidateQueries({ queryKey: ['respostas', 'detail', data.id] });
    },
  });
}
