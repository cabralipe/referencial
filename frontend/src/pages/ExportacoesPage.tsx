import { FormEvent, useEffect, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateExportJob, useExportJobs } from '@/hooks/useExportJobs';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useQuadros } from '@/hooks/useQuadros';
import { useTextoUnicos } from '@/hooks/useTextoUnico';
import { useTarefas } from '@/hooks/useTarefas';

import './ExportacoesPage.css';

const FORMATS = ['pdf', 'docx'];

const EXPORT_TARGETS = [
  { value: 'texto_unico', label: 'Texto único' },
  { value: 'quadro', label: 'Quadro' },
];

const STATUS_LABEL: Record<string, string> = {
  queued: 'Na fila',
  running: 'Em execução',
  done: 'Concluído',
  error: 'Erro',
};

export function ExportacoesPage() {
  const [alvoTipoFiltro, setAlvoTipoFiltro] = useState('');
  const [alvoIdFiltro, setAlvoIdFiltro] = useState('');
  const [novoAlvoTipo, setNovoAlvoTipo] = useState(EXPORT_TARGETS[0]?.value ?? 'texto_unico');
  const [textoUnicoGtId, setTextoUnicoGtId] = useState<number | ''>('');
  const [novoAlvoId, setNovoAlvoId] = useState('');
  const [novoFormato, setNovoFormato] = useState(FORMATS[0]);

  const { data: exportsJobs, isLoading, refetch, isFetching } = useExportJobs({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdFiltro ? Number(alvoIdFiltro) : undefined,
  });
  const criarExportacao = useCreateExportJob();
  const { gtOptions, isLoading: isLoadingGts } = useAvailableGts({ scope: 'all' });
  const { data: tarefas } = useTarefas();
  const { data: quadros, isLoading: isLoadingQuadros } = useQuadros();
  const { data: textoUnicos, isLoading: isLoadingTextoUnicos, isFetching: isFetchingTextoUnicos } = useTextoUnicos({
    gtId: novoAlvoTipo === 'texto_unico' && typeof textoUnicoGtId === 'number' ? textoUnicoGtId : undefined,
  });

  useEffect(() => {
    if (novoAlvoTipo !== 'texto_unico') {
      return;
    }
    if (!textoUnicoGtId && gtOptions.length > 0) {
      setTextoUnicoGtId(gtOptions[0].id);
    }
  }, [gtOptions, novoAlvoTipo, textoUnicoGtId]);

  useEffect(() => {
    setNovoAlvoId('');
  }, [novoAlvoTipo, textoUnicoGtId]);

  const gtsById = useMemo(() => {
    const map = new Map<number, string>();
    gtOptions.forEach((gt) => {
      map.set(gt.id, gt.displayName);
    });
    return map;
  }, [gtOptions]);

  const tarefasById = useMemo(() => {
    const map = new Map<number, string>();
    tarefas?.forEach((tarefa) => {
      map.set(tarefa.id, tarefa.nome);
    });
    return map;
  }, [tarefas]);

  const textoUnicoOptions = useMemo(() => {
    if (!textoUnicos) return [];
    return textoUnicos.map((item) => {
      const gtLabel = gtsById.get(item.gt) ?? `GT #${item.gt}`;
      const tarefaLabel = tarefasById.get(item.tarefa);
      const tarefaText = tarefaLabel ? `${tarefaLabel} (#${item.tarefa})` : `Tarefa #${item.tarefa}`;
      return {
        value: String(item.id),
        label: `Texto único #${item.id} — ${gtLabel} — ${tarefaText}`,
      };
    });
  }, [gtsById, tarefasById, textoUnicos]);

  const quadroOptions = useMemo(() => {
    if (!quadros) return [];
    return quadros.map((quadro) => {
      const gtLabel = gtsById.get(quadro.gt) ?? `GT #${quadro.gt}`;
      return {
        value: String(quadro.id),
        label: `Quadro #${quadro.id} — ${quadro.template} — ${gtLabel}`,
      };
    });
  }, [gtsById, quadros]);

  const alvoOptions = useMemo(() => {
    if (novoAlvoTipo === 'texto_unico') {
      return textoUnicoOptions;
    }
    if (novoAlvoTipo === 'quadro') {
      return quadroOptions;
    }
    return [];
  }, [novoAlvoTipo, quadroOptions, textoUnicoOptions]);

  useEffect(() => {
    if (!novoAlvoId && alvoOptions.length > 0) {
      setNovoAlvoId(alvoOptions[0].value);
    }
  }, [alvoOptions, novoAlvoId]);

  const precisaSelecionarGt = novoAlvoTipo === 'texto_unico' && !textoUnicoGtId;
  const carregandoAlvos =
    novoAlvoTipo === 'texto_unico'
      ? precisaSelecionarGt || isLoadingTextoUnicos || isFetchingTextoUnicos
      : isLoadingQuadros || !quadros;

  const alvoPlaceholder = (() => {
    if (precisaSelecionarGt) {
      return 'Selecione um GT para listar os textos únicos';
    }
    if (carregandoAlvos) {
      return 'Carregando alvos...';
    }
    if (alvoOptions.length === 0) {
      return 'Nenhum registro encontrado para este filtro';
    }
    return 'Selecione um registro';
  })();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const alvoTipo = novoAlvoTipo.trim();
    const alvoId = Number(novoAlvoId);
    const formato = novoFormato || 'pdf';
    if (!alvoTipo || !alvoId) {
      return;
    }
    await criarExportacao.mutateAsync({ alvoTipo, alvoId, formato });
    setNovoAlvoId('');
    refetch();
  };

  if (isLoading && !exportsJobs) {
    return <FullPageLoader message="Carregando exportações..." />;
  }

  return (
    <div className="exportacoes">
      <header className="exportacoes__header">
        <div>
          <h1>Exportações</h1>
          <p>Gere relatórios e documentos oficiais a partir dos conteúdos publicados.</p>
        </div>
      </header>

      <PageInstructions
        title="Checklist antes de exportar"
        description="Reúna informações necessárias para configurar a exportação com sucesso."
        items={[
          {
            title: 'Identifique o alvo',
            description: 'Escolha o tipo de entidade (Texto único ou Quadro) e selecione o registro pelo nome.',
          },
          {
            title: 'Escolha o formato',
            description: 'PDF atende visualização rápida; DOCX facilita novas edições pelo time editorial.',
          },
          {
            title: 'Monitore o status',
            description: 'Jobs ficam em processamento até ficarem disponíveis para download via URL resultante.',
          },
        ]}
      />

      <div className="exportacoes__filters">
        <label>
          <span>Filtrar por alvo</span>
          <select value={alvoTipoFiltro} onChange={(event) => setAlvoTipoFiltro(event.target.value)}>
            <option value="">Todos</option>
            {EXPORT_TARGETS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Filtrar por ID</span>
          <input
            type="number"
            value={alvoIdFiltro}
            onChange={(event) => setAlvoIdFiltro(event.target.value)}
            placeholder="Ex.: 12"
          />
        </label>
        <button type="button" className="ghost" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? 'Atualizando...' : 'Aplicar filtros'}
        </button>
      </div>

      <section className="exportacoes__nova">
        <h2>Nova exportação</h2>
        <form onSubmit={handleSubmit}>
          <label>
            <span>Alvo tipo</span>
            <select name="alvoTipo" value={novoAlvoTipo} onChange={(e) => setNovoAlvoTipo(e.target.value)} required>
              {EXPORT_TARGETS.map((item) => (
                <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          </label>
          {novoAlvoTipo === 'texto_unico' && (
            <label>
              <span>GT do texto único</span>
              <select
                value={textoUnicoGtId === '' ? '' : String(textoUnicoGtId)}
                onChange={(event) => setTextoUnicoGtId(event.target.value ? Number(event.target.value) : '')}
                disabled={isLoadingGts || gtOptions.length === 0}
                required
              >
                <option value="" disabled>
                  {isLoadingGts ? 'Carregando GTs...' : 'Selecione um GT'}
                </option>
                {gtOptions.map((gt) => (
                  <option key={gt.id} value={gt.id}>
                    {gt.displayName}
                  </option>
                ))}
              </select>
              <small className="exportacoes__hint">Filtre rapidamente para listar textos únicos do GT selecionado.</small>
            </label>
          )}
          <label className="full">
            <span>Selecione o alvo</span>
            <select
              name="alvoId"
              value={novoAlvoId}
              onChange={(e) => setNovoAlvoId(e.target.value)}
              required
              disabled={carregandoAlvos || alvoOptions.length === 0}
            >
              <option value="" disabled>
                {alvoPlaceholder}
              </option>
              {alvoOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <small className="exportacoes__hint">
              Escolha o registro pelo nome — sem precisar decorar IDs.
            </small>
          </label>
          <label>
            <span>Formato</span>
            <select name="formato" value={novoFormato} onChange={(e) => setNovoFormato(e.target.value)}>
              {FORMATS.map((format) => (
                <option key={format} value={format}>
                  {format.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={criarExportacao.isPending}>
            {criarExportacao.isPending ? 'Agendando...' : 'Criar exportação'}
          </button>
        </form>
      </section>

      <div className="exportacoes__lista">
        <div className="exportacoes__lista-header">
          <h2>Histórico ({exportsJobs?.length ?? 0})</h2>
        </div>

        {exportsJobs && exportsJobs.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Alvo</th>
                <th>Formato</th>
                <th>Status</th>
                <th>Solicitado</th>
                <th>Finalizado</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {exportsJobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.id}</td>
                  <td>
                    {job.alvo_tipo} #{job.alvo_id}
                  </td>
                  <td>{job.formato.toUpperCase()}</td>
                  <td>{STATUS_LABEL[job.status] ?? job.status}</td>
                  <td>{new Date(job.created_at).toLocaleString('pt-BR')}</td>
                  <td>{job.finished_at ? new Date(job.finished_at).toLocaleString('pt-BR') : '—'}</td>
                  <td>
                    {job.url_resultado ? (
                      <a href={job.url_resultado} target="_blank" rel="noreferrer">
                        Download
                      </a>
                    ) : (
                      'Pendente'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="exportacoes__empty">
            <p>Nenhuma exportação cadastrada. Agende um job para vê-lo aqui.</p>
          </div>
        )}
      </div>
    </div>
  );
}
