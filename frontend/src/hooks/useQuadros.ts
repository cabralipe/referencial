import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { CelulaQuadro, PaginatedResponse, Quadro } from '@/api/types';

interface UseQuadrosParams {
  areaId?: number;
  gtId?: number;
  template?: string;
}

export function useQuadros({ areaId, gtId, template }: UseQuadrosParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['quadros', { areaId, gtId, template }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Quadro>>('/quadro', {
        query: {
          area_id: areaId,
          gt_id: gtId,
          template,
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface UpdateCelulaInput {
  quadroId: number;
  linha: number;
  coluna: number;
  valor_html: string;
}

export function useUpdateCelulaQuadro() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ quadroId, linha, coluna, valor_html }: UpdateCelulaInput) => {
      const response = await client.put<CelulaQuadro>(`/quadro/${quadroId}/celula`, {
        body: { linha, coluna, valor_html },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quadros'] });
    },
  });
}
