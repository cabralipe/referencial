import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import { fetchAllPaginated } from '@/utils/pagination';
import type { CampoFormulario, FormularioInscricao, FormularioInscricaoPublic, InscricaoPublica } from '@/api/types';

export function useFormulariosInscricao() {
  const client = useApiClient();
  const { cliente, user, status } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;
  const enabled = status === 'authenticated' && Boolean(clienteId);

  return useQuery({
    queryKey: ['formularios_inscricao', clienteId],
    enabled,
    queryFn: async () => {
      if (!clienteId) {
        throw new Error('Cliente não identificado para carregar formulários.');
      }
      return fetchAllPaginated<FormularioInscricao>(client.get, '/formularios_inscricao', {
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
    },
  });
}

interface CriarFormularioInput {
  titulo: string;
  subtitulo?: string;
  descricao?: string;
  ativo?: boolean;
  opcoes_area_atuacao?: string[];
  opcoes_representacao?: string[];
  campos_config?: CampoFormulario[];
  imagem_hero?: File;
}

export function useCriarFormularioInscricao() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useMutation({
    mutationFn: async (payload: CriarFormularioInput) => {
      const form = new FormData();
      form.append('titulo', payload.titulo);
      if (payload.subtitulo) form.append('subtitulo', payload.subtitulo);
      if (payload.descricao) form.append('descricao', payload.descricao);
      form.append('ativo', payload.ativo === false ? 'false' : 'true');
      if (payload.opcoes_area_atuacao) {
        form.append('opcoes_area_atuacao', JSON.stringify(payload.opcoes_area_atuacao));
      }
      if (payload.opcoes_representacao) {
        form.append('opcoes_representacao', JSON.stringify(payload.opcoes_representacao));
      }
      if (payload.campos_config) {
        form.append('campos_config', JSON.stringify(payload.campos_config));
      }
      if (payload.imagem_hero) {
        form.append('imagem_hero', payload.imagem_hero);
      }

      const response = await client.post<FormularioInscricao>('/formularios_inscricao', {
        body: form,
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['formularios_inscricao', clienteId] });
    },
  });
}

export interface EditarFormularioInput extends Partial<CriarFormularioInput> {
  id: number;
}

export function useEditarFormularioInscricao() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useMutation({
    mutationFn: async ({ id, ...payload }: EditarFormularioInput) => {
      const form = new FormData();
      if (payload.titulo) form.append('titulo', payload.titulo);
      if (payload.subtitulo !== undefined) form.append('subtitulo', payload.subtitulo);
      if (payload.descricao !== undefined) form.append('descricao', payload.descricao);
      if (payload.ativo !== undefined) form.append('ativo', payload.ativo ? 'true' : 'false');
      if (payload.opcoes_area_atuacao) {
        form.append('opcoes_area_atuacao', JSON.stringify(payload.opcoes_area_atuacao));
      }
      if (payload.opcoes_representacao) {
        form.append('opcoes_representacao', JSON.stringify(payload.opcoes_representacao));
      }
      if (payload.campos_config !== undefined) {
        form.append('campos_config', JSON.stringify(payload.campos_config));
      }
      if (payload.imagem_hero) {
        form.append('imagem_hero', payload.imagem_hero);
      }

      const response = await client.patch<FormularioInscricao>(`/formularios_inscricao/${id}`, {
        body: form,
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['formularios_inscricao', clienteId] });
    },
  });
}

export function useExcluirFormularioInscricao() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useMutation({
    mutationFn: async (id: number) => {
      await client.del(`/formularios_inscricao/${id}`, {
        headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['formularios_inscricao', clienteId] });
    },
  });
}

export function useInscricoesFormulario(formularioId?: number, nomeFiltro?: string) {
  const client = useApiClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useQuery({
    queryKey: ['formularios_inscricao', formularioId, 'inscricoes', nomeFiltro],
    enabled: Boolean(formularioId),
    queryFn: async () => {
      const params = nomeFiltro ? `?nome_completo=${encodeURIComponent(nomeFiltro)}` : '';
      const response = await client.get<InscricaoPublica[]>(
        `/formularios_inscricao/${formularioId}/inscricoes${params}`,
        { headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined },
      );
      return response.data;
    },
  });
}

export function useFormularioInscricaoPublic(token?: string) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['formulario_inscricao_public', token],
    enabled: Boolean(token),
    staleTime: 0,
    queryFn: async () => {
      const response = await client.get<FormularioInscricaoPublic>(
        `/formularios_inscricao/public/${token}`,
        { skipAuth: true },
      );
      return response.data;
    },
  });
}

interface EnviarInscricaoInput {
  token: string;
  nome_completo: string;
  instituicao_comunidade?: string;
  telefone?: string;
  email?: string;
  areas_atuacao?: string[];
  area_atuacao_outro?: string;
  representacoes?: string[];
  representacao_outro?: string;
  dados_extras?: Record<string, unknown>;
}

export function useEnviarInscricao() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async ({ token, ...payload }: EnviarInscricaoInput) => {
      const response = await client.post<InscricaoPublica>(
        `/formularios_inscricao/public/${token}/inscricoes`,
        { body: payload, skipAuth: true },
      );
      return response.data;
    },
  });
}
