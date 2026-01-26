import { useMutation } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';

interface ContinuarResponse {
  url: string;
  status?: string;
  gt_id?: number;
  tarefa_id?: number;
  pergunta_id?: number;
  resposta_id?: number | null;
  message?: string;
}

export function useContinuar() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async () => {
      const response = await client.get<ContinuarResponse>('/continuar');
      return response.data;
    },
  });
}
