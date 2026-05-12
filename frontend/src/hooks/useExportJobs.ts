import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { ExportJob, PaginatedResponse } from '@/api/types';

interface UseExportJobsParams {
  alvoTipo?: string;
  alvoId?: number | string;
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
  alvoId: number | string;
  formato: string;
  payloadJson?: Record<string, unknown>;
}


export function useCreateExportJob() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ alvoTipo, alvoId, formato, payloadJson }: CreateExportJobInput) => {
      const response = await client.post<ExportJob>('/exports', {
        body: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          formato,
          payload_json: payloadJson,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['export-jobs'] });
    },
  });
}

export function useDownloadExport() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ alvoTipo, alvoId, formato, payloadJson }: CreateExportJobInput) => {
      const response = await client.post<Blob>('/exports/download', {
        body: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          formato,
          payload_json: payloadJson,
        },
        responseType: 'blob',
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['export-jobs'] });
    },
  });
}

