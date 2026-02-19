import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import type {
  ConsultaPublica,
  ConsultaPublicaPublic,
  ManifestacaoPublica,
  ManifestacaoPublicaPublic,
  PaginatedResponse,
} from '@/api/types';

export function useConsultasPublicas() {
  const client = useApiClient();
  const { cliente, user, status } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;
  const enabled = status === 'authenticated' && Boolean(clienteId);

  return useQuery({
    queryKey: ['consultas_publicas', clienteId],
    enabled,
    queryFn: async () => {
      if (!clienteId) {
        throw new Error('Cliente não identificado para carregar consultas.');
      }
      const response = await client.get<PaginatedResponse<ConsultaPublica>>('/consultas_publicas', {
        query: { page_size: 200 },
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
      return response.data.results ?? [];
    },
  });
}

interface CriarConsultaPublicaInput {
  titulo: string;
  slug?: string;
  descricao?: string;
  pdf: File;
  data_publicacao: string;
  data_validade?: string;
  data_fechamento?: string;
  perguntas_votacao?: { pergunta: string; opcoes: string[] }[];
  ativa?: boolean;
}

export function useCriarConsultaPublica() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useMutation({
    mutationFn: async (payload: CriarConsultaPublicaInput) => {
      if (!clienteId) {
        throw new Error('Cliente não identificado para criar consulta.');
      }
      const mime = payload.pdf?.type?.toLowerCase?.() ?? '';
      const nomeArquivo = payload.pdf?.name?.toLowerCase?.() ?? '';
      if (!payload.pdf || (!mime.includes('pdf') && !nomeArquivo.endsWith('.pdf'))) {
        throw new Error('Envie um arquivo PDF válido.');
      }
      if (payload.pdf.size === 0) {
        throw new Error('O PDF está vazio. Tente reenviar o arquivo.');
      }
      const form = new FormData();
      form.append('titulo', payload.titulo);
      if (payload.slug) form.append('slug', payload.slug);
      if (payload.descricao) form.append('descricao', payload.descricao);
      form.append('pdf', payload.pdf);
      form.append('data_publicacao', payload.data_publicacao);
      if (payload.data_validade) form.append('data_validade', payload.data_validade);
      if (payload.data_fechamento) form.append('data_fechamento', payload.data_fechamento);
      if (payload.perguntas_votacao && payload.perguntas_votacao.length > 0) {
        form.append('perguntas_votacao', JSON.stringify(payload.perguntas_votacao));
      }
      form.append('ativa', payload.ativa === false ? 'false' : 'true');

      const response = await client.post<ConsultaPublica>('/consultas_publicas', {
        body: form,
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consultas_publicas', clienteId] });
    },
  });
}

export function useManifestacoesConsulta(consultaId?: number) {
  const client = useApiClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useQuery({
    queryKey: ['consultas_publicas', consultaId, 'manifestacoes'],
    enabled: Boolean(consultaId),
    queryFn: async () => {
      const response = await client.get<ManifestacaoPublica[]>(`/consultas_publicas/${consultaId}/manifestacoes`, {
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
      return response.data;
    },
  });
}

export function useConsultaPublicaPublic(token?: string) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['consulta_publica_public', token],
    enabled: Boolean(token),
    queryFn: async () => {
      const response = await client.get<ConsultaPublicaPublic>(`/consultas_publicas/public/${token}`, {
        skipAuth: true,
      });
      return response.data;
    },
  });
}

export function useManifestacoesPublicas(token?: string) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['consulta_publica_public', token, 'manifestacoes'],
    enabled: Boolean(token),
    queryFn: async () => {
      const response = await client.get<ManifestacaoPublicaPublic[]>(
        `/consultas_publicas/public/${token}/manifestacoes`,
        { skipAuth: true },
      );
      return response.data;
    },
  });
}

interface EnviarManifestacaoInput {
  token: string;
  pagina?: number | null;
  comentario?: string;
  votos?: string[];
  nome_completo: string;
  cpf: string;
  cidade: string;
  estado: string;
  contato_email?: string;
}

export function useEnviarManifestacao() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ token, ...payload }: EnviarManifestacaoInput) => {
      const response = await client.post<ManifestacaoPublicaPublic>(
        `/consultas_publicas/public/${token}/manifestacoes`,
        {
          body: payload,
          skipAuth: true,
        },
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['consulta_publica_public', variables.token, 'manifestacoes'] });
      queryClient.invalidateQueries({ queryKey: ['consulta_publica_public', variables.token] });
    },
  });
}

export function useExcluirConsultaPublica() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useMutation({
    mutationFn: async (consultaId: number) => {
      if (!clienteId) {
        throw new Error('Cliente não identificado para excluir consulta.');
      }
      await client.del(`/consultas_publicas/${consultaId}`, {
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consultas_publicas', clienteId] });
    },
  });
}
