import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { ExportJob, PaginatedResponse } from '@/api/types';

interface UseExportJobsParams {
  alvoTipo?: string;
  alvoId?: number;
}

export function useExportJobs({ alvoId, alvoTipo }: UseExportJobsParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['export-jobs', { alvoId, alvoTipo }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<ExportJob>>('/exports', {
        query: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          page_size: 100,
        },
      });
      return response.data.results ?? [];
    },
    refetchInterval: 30_000,
  });
}

interface CreateExportJobInput {
  alvoTipo: string;
  alvoId: number;
  formato: string;
}

export function useCreateExportJob() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ alvoTipo, alvoId, formato }: CreateExportJobInput) => {
      const response = await client.post<ExportJob>('/exports', {
        body: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          formato,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['export-jobs'] });
    },
  });
}
