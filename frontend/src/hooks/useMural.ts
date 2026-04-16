import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { MuralPost } from '@/api/types';

interface UseMuralParams {
  enabled?: boolean;
}

export function useMural({ enabled = true }: UseMuralParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['mural', 'posts'],
    enabled,
    queryFn: async () => {
      const response = await client.get<MuralPost[]>('/mural');
      return response.data ?? [];
    },
  });
}

export function useCreateMuralPost() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: FormData | Record<string, unknown>) => {
      const response = await client.post<MuralPost>('/mural', { body: payload });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mural', 'posts'] });
    },
  });
}

interface UpdateMuralPostInput {
  id: string;
  payload: FormData | Record<string, unknown>;
}

export function useUpdateMuralPost() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: UpdateMuralPostInput) => {
      const response = await client.put<MuralPost>(`/mural/${id}`, { body: payload });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mural', 'posts'] });
    },
  });
}

export function useDeleteMuralPost() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await client.delete(`/mural/${id}`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mural', 'posts'] });
    },
  });
}

interface SubmitMuralFileInput {
  id: string;
  payload: FormData;
}

export function useSubmitMuralFile() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: SubmitMuralFileInput) => {
      const response = await client.post(`/mural/${id}/envios`, { body: payload });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mural', 'posts'] });
    },
  });
}
