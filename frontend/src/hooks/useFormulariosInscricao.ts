import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import { fetchAllPaginated } from '@/utils/pagination';
import type {
  CampoFormulario,
  FormularioInscricao,
  FormularioInscricaoAnexo,
  FormularioInscricaoPublic,
  InscricaoPublica,
} from '@/api/types';

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

export function useAnexosFormularioInscricao(formularioId?: number) {
  const client = useApiClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useQuery({
    queryKey: ['formularios_inscricao', formularioId, 'anexos'],
    enabled: Boolean(formularioId),
    queryFn: async () => {
      const response = await client.get<FormularioInscricaoAnexo[]>(
        `/formularios_inscricao/${formularioId}/anexos`,
        { headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined },
      );
      return response.data;
    },
  });
}

export function useBaixarAnexosFormularioInscricao() {
  const client = useApiClient();
  const { cliente, user } = useAuth();
  const clienteId = cliente?.cliente?.id ?? user?.clienteId ?? null;

  return useMutation({
    mutationFn: async ({ formularioId, ids }: { formularioId: number; ids: string[] }) => {
      const response = await client.post<Blob>(
        `/formularios_inscricao/${formularioId}/anexos/download`,
        {
          body: { ids },
          headers: clienteId ? { 'X-Cliente-ID': String(clienteId) } : undefined,
          responseType: 'blob',
        },
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
  arquivos?: Record<string, File | null | undefined>;
}

export function useEnviarInscricao() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async ({ token, arquivos, ...payload }: EnviarInscricaoInput) => {
      const arquivosValidos = Object.entries(arquivos ?? {}).filter(([, arquivo]) => arquivo instanceof File);
      if (arquivosValidos.length > 0) {
        const form = new FormData();
        form.append('nome_completo', payload.nome_completo);
        if (payload.instituicao_comunidade) form.append('instituicao_comunidade', payload.instituicao_comunidade);
        if (payload.telefone) form.append('telefone', payload.telefone);
        if (payload.email) form.append('email', payload.email);
        if (payload.areas_atuacao) form.append('areas_atuacao', JSON.stringify(payload.areas_atuacao));
        if (payload.area_atuacao_outro) form.append('area_atuacao_outro', payload.area_atuacao_outro);
        if (payload.representacoes) form.append('representacoes', JSON.stringify(payload.representacoes));
        if (payload.representacao_outro) form.append('representacao_outro', payload.representacao_outro);
        if (payload.dados_extras) form.append('dados_extras', JSON.stringify(payload.dados_extras));
        arquivosValidos.forEach(([chave, arquivo]) => {
          form.append(chave, arquivo as File);
        });
        const response = await client.post<InscricaoPublica>(
          `/formularios_inscricao/public/${token}/inscricoes`,
          { body: form, skipAuth: true },
        );
        return response.data;
      }

      const response = await client.post<InscricaoPublica>(
        `/formularios_inscricao/public/${token}/inscricoes`,
        { body: payload, skipAuth: true },
      );
      return response.data;
    },
  });
}
