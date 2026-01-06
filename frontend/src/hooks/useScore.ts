import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';

export interface ScoreSummary {
  current_points: number;
  monthly_limit: number;
  progress: number;
  default_points?: number;
}

export interface ScoreConfig {
  monthly_limit: number;
  default_points: number;
  tarefa_points: Record<string, number>;
}

export function useScoreSummary() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['score', 'summary'],
    queryFn: async () => {
      const response = await client.get<ScoreSummary>('/score/summary');
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}

export function useScoreConfig() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['score', 'config'],
    queryFn: async () => {
      const response = await client.get<ScoreConfig>('/score/config');
      return response.data;
    },
  });

  const update = useMutation({
    mutationFn: async (payload: Partial<ScoreConfig>) => {
      const response = await client.patch<ScoreConfig>('/score/config', {
        body: payload,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['score', 'config'] });
      queryClient.invalidateQueries({ queryKey: ['score', 'summary'] });
    },
  });

  return {
    ...query,
    update,
  };
}
