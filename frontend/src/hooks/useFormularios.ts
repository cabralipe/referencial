import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type {
  CampoDinamico,
  FormularioDinamico,
  PaginatedResponse,
  RespostaCampoDinamico,
} from '@/api/types';

export function useFormularios() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['formularios'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<FormularioDinamico>>('/formularios', {
        query: {
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

export function useCamposFormulario(formularioId?: number) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(formularioId),
    queryKey: ['formularios', formularioId, 'campos'],
    queryFn: async () => {
      const response = await client.get<CampoDinamico[]>(`/formularios/${formularioId}/campos`);
      return response.data;
    },
  });
}

interface CreateFormularioInput {
  nome: string;
  descricao?: string;
  ativo?: boolean;
}

export function useCreateFormulario() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ nome, descricao, ativo }: CreateFormularioInput) => {
      const response = await client.post<FormularioDinamico>('/formularios', {
        body: {
          nome,
          descricao,
          ativo,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['formularios'] });
    },
  });
}

interface CreateCampoInput {
  formularioId: number;
  chave: string;
  tipo: string;
  obrigatorio?: boolean;
  ordem?: number;
  config_json?: Record<string, unknown>;
}

export function useCreateCampoFormulario() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ formularioId, ...payload }: CreateCampoInput) => {
      const response = await client.post<CampoDinamico>(`/formularios/${formularioId}/campos`, {
        body: payload,
      });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['formularios', variables.formularioId, 'campos'] });
    },
  });
}

interface SubmitFormularioInput {
  formularioId: number;
  respostas: Array<{
    campo: CampoDinamico;
    valor: string | number | boolean | null;
  }>;
  ownerType?: string;
  ownerId?: number;
}

export function useSubmitFormulario() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ formularioId, respostas, ownerId, ownerType }: SubmitFormularioInput) => {
      const created: RespostaCampoDinamico[] = [];
      for (const entrada of respostas) {
        const payload: Record<string, unknown> = {
          formulario: formularioId,
          campo: entrada.campo.id,
          owner_type: ownerType,
          owner_id: ownerId,
        };
        const tipo = entrada.campo.tipo?.toLowerCase() ?? 'texto';
        if (tipo.includes('bool')) {
          payload.valor_bool = Boolean(entrada.valor);
          payload.valor_texto = null;
          payload.valor_num = null;
        } else if (tipo.includes('num')) {
          const numero = typeof entrada.valor === 'number' ? entrada.valor : Number(entrada.valor);
          payload.valor_num = Number.isFinite(numero) ? numero : null;
          payload.valor_texto = null;
          payload.valor_bool = null;
        } else {
          payload.valor_texto = entrada.valor ?? '';
          payload.valor_num = null;
          payload.valor_bool = null;
        }
        const response = await client.post<RespostaCampoDinamico>(`/formularios/${formularioId}/respostas`, {
          body: payload,
        });
        created.push(response.data);
      }
      return created;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['formularios', variables.formularioId, 'respostas'] });
    },
  });
}
