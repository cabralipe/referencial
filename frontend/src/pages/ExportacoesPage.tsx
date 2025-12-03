import { FormEvent, useEffect, useMemo, useState } from 'react';

import type { ExportJob } from '@/api/types';
import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateExportJob, useExportJobs } from '@/hooks/useExportJobs';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useQuadros } from '@/hooks/useQuadros';
import { useTextoUnicos } from '@/hooks/useTextoUnico';
import { useTarefas } from '@/hooks/useTarefas';
import { useRespostas } from '@/hooks/useRespostas';

import './ExportacoesPage.css';

const FORMATS = ['pdf', 'docx'];

const EXPORT_TARGETS = [
  { value: 'texto_unico', label: 'Texto único' },
  { value: 'resposta', label: 'Resposta' },
  { value: 'quadro', label: 'Perguntas (quadro)' },
  { value: 'colecao', label: 'Sequência personalizada' },
];

const STATUS_LABEL: Record<string, string> = {
  queued: 'Na fila',
  running: 'Em execução',
  done: 'Concluído',
  error: 'Erro',
};

export function ExportacoesPage() {
  const [alvoTipoFiltro, setAlvoTipoFiltro] = useState('');
  const [filtroGtId, setFiltroGtId] = useState('');
  const [alvoIdFiltro, setAlvoIdFiltro] = useState('');
  const [novoAlvoTipo, setNovoAlvoTipo] = useState(EXPORT_TARGETS[0]?.value ?? 'texto_unico');
  const [textoUnicoGtId, setTextoUnicoGtId] = useState<number | ''>('');
  const [respostaGtId, setRespostaGtId] = useState<number | ''>('');
  const [novoAlvoId, setNovoAlvoId] = useState('');
  const [novoFormato, setNovoFormato] = useState(FORMATS[0]);
  const [colecaoGtId, setColecaoGtId] = useState<number | ''>('');
  const [colecaoFonteTipo, setColecaoFonteTipo] = useState<'resposta' | 'texto_unico'>('resposta');
  const [colecaoAlvoId, setColecaoAlvoId] = useState('');
  const [colecaoTitulo, setColecaoTitulo] = useState('Documento personalizado');
  const [colecaoItens, setColecaoItens] = useState<
    { id: number; tipo: 'texto_unico' | 'resposta'; label: string; gtId?: number | null }[]
  >([]);

  const { data: exportsJobs, isLoading, refetch, isFetching } = useExportJobs({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdFiltro || undefined,
  });
  const criarExportacao = useCreateExportJob();
  const { gtOptions, isLoading: isLoadingGts } = useAvailableGts({ scope: 'all' });
  const { data: tarefas } = useTarefas();
  const { data: quadros, isLoading: isLoadingQuadros } = useQuadros();
  const {
    data: textoUnicosPorGt,
    isLoading: isLoadingTextoUnicos,
    isFetching: isFetchingTextoUnicos,
  } = useTextoUnicos({
    gtId: novoAlvoTipo === 'texto_unico' && typeof textoUnicoGtId === 'number' ? textoUnicoGtId : undefined,
  });
  const { data: todosTextoUnicos, isLoading: isLoadingTodosTextoUnicos } = useTextoUnicos({ includeAll: true });
  const { data: respostas, isLoading: isLoadingRespostas } = useRespostas({ includeAll: true });

  useEffect(() => {
    if (novoAlvoTipo === 'texto_unico' && !textoUnicoGtId && gtOptions.length > 0) {
      setTextoUnicoGtId(gtOptions[0].id);
    }
    if (novoAlvoTipo === 'resposta' && !respostaGtId && gtOptions.length > 0) {
      setRespostaGtId(gtOptions[0].id);
    }
  }, [gtOptions, novoAlvoTipo, respostaGtId, textoUnicoGtId]);

  useEffect(() => {
    if (!colecaoGtId && gtOptions.length > 0) {
      setColecaoGtId(gtOptions[0].id);
    }
  }, [colecaoGtId, gtOptions]);

  useEffect(() => {
    setNovoAlvoId('');
  }, [novoAlvoTipo, textoUnicoGtId, respostaGtId]);

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
    if (!textoUnicosPorGt) return [];
    return textoUnicosPorGt.map((item) => {
      const gtLabel = gtsById.get(item.gt) ?? `GT #${item.gt}`;
      const tarefaLabel = tarefasById.get(item.tarefa);
      const tarefaText = tarefaLabel ? `${tarefaLabel} (#${item.tarefa})` : `Tarefa #${item.tarefa}`;
      return {
        value: String(item.id),
        label: `Texto único #${item.id} — ${gtLabel} — ${tarefaText}`,
        gtId: item.gt,
      };
    });
  }, [gtsById, tarefasById, textoUnicosPorGt]);

  const todosTextoUnicoOptions = useMemo(() => {
    if (!todosTextoUnicos) return [];
    return todosTextoUnicos.map((item) => {
      const gtLabel = gtsById.get(item.gt) ?? `GT #${item.gt}`;
      const tarefaLabel = tarefasById.get(item.tarefa);
      const tarefaText = tarefaLabel ? `${tarefaLabel} (#${item.tarefa})` : `Tarefa #${item.tarefa}`;
      return {
        value: String(item.id),
        label: `Texto único #${item.id} — ${gtLabel} — ${tarefaText}`,
        gtId: item.gt,
      };
    });
  }, [gtsById, tarefasById, todosTextoUnicos]);

  const respostaOptions = useMemo(() => {
    if (!respostas) return [];
    return respostas.map((resp) => {
      const gtLabel = gtsById.get(resp.gt) ?? `GT #${resp.gt}`;
      const pergunta = resp.pergunta_texto || `Pergunta #${resp.pergunta}`;
      const prefixo = resp.pergunta_ordem ? `${resp.pergunta_ordem}. ` : '';
      return {
        value: String(resp.id),
        label: `${gtLabel} — ${prefixo}${pergunta}`,
        gtId: resp.gt,
      };
    });
  }, [gtsById, respostas]);

  const respostaOptionsPorGt = useMemo(() => {
    const gtFilter = typeof respostaGtId === 'number' ? respostaGtId : null;
    if (!gtFilter) return respostaOptions;
    return respostaOptions.filter((resp) => resp.gtId === gtFilter);
  }, [respostaGtId, respostaOptions]);

  const quadroOptions = useMemo(() => {
    if (!quadros) return [];
    return quadros.map((quadro) => {
      const gtLabel = gtsById.get(quadro.gt) ?? `GT #${quadro.gt}`;
      return {
        value: String(quadro.id),
        label: `Perguntas (quadro) #${quadro.id} — ${quadro.template} — ${gtLabel}`,
        gtId: quadro.gt,
      };
    });
  }, [gtsById, quadros]);

  const filtroAlvoOptions = useMemo(() => {
    const baseRespostas = respostaOptions;
    const baseTextos = todosTextoUnicoOptions;
    const baseQuadros = quadroOptions;
    let base: typeof baseTextos = [];
    if (alvoTipoFiltro === 'resposta') {
      base = baseRespostas;
    } else if (alvoTipoFiltro === 'texto_unico') {
      base = baseTextos;
    } else if (alvoTipoFiltro === 'quadro') {
      base = baseQuadros;
    } else {
      base = [...baseRespostas, ...baseTextos, ...baseQuadros];
    }
    const gtFilter = filtroGtId ? Number(filtroGtId) : null;
    return gtFilter ? base.filter((item) => item.gtId === gtFilter) : base;
  }, [alvoTipoFiltro, filtroGtId, quadroOptions, respostaOptions, todosTextoUnicoOptions]);

  const alvoOptions = useMemo(() => {
    if (novoAlvoTipo === 'texto_unico') {
      return textoUnicoOptions;
    }
    if (novoAlvoTipo === 'resposta') {
      return respostaOptionsPorGt;
    }
    if (novoAlvoTipo === 'quadro') {
      return quadroOptions;
    }
    return [];
  }, [novoAlvoTipo, quadroOptions, respostaOptionsPorGt, textoUnicoOptions]);

  const colecaoOptions = useMemo(() => {
    const base = colecaoFonteTipo === 'resposta' ? respostaOptions : todosTextoUnicoOptions;
    const gtFilter = typeof colecaoGtId === 'number' ? colecaoGtId : null;
    if (!gtFilter) return base;
    return base.filter((item) => item.gtId === gtFilter);
  }, [colecaoFonteTipo, colecaoGtId, respostaOptions, todosTextoUnicoOptions]);

  useEffect(() => {
    if (!novoAlvoId && alvoOptions.length > 0) {
      setNovoAlvoId(alvoOptions[0].value);
    }
  }, [alvoOptions, novoAlvoId]);

  useEffect(() => {
    if (!colecaoAlvoId && colecaoOptions.length > 0) {
      setColecaoAlvoId(colecaoOptions[0].value);
    }
  }, [colecaoAlvoId, colecaoOptions]);

  useEffect(() => {
    setAlvoIdFiltro('');
  }, [alvoTipoFiltro, filtroGtId]);

  const precisaSelecionarGt =
    (novoAlvoTipo === 'texto_unico' && !textoUnicoGtId) || (novoAlvoTipo === 'resposta' && !respostaGtId);
  const carregandoAlvos =
    novoAlvoTipo === 'texto_unico'
      ? precisaSelecionarGt || isLoadingTextoUnicos || isFetchingTextoUnicos
      : novoAlvoTipo === 'resposta'
        ? isLoadingRespostas
        : isLoadingQuadros || !quadros;

  const alvoPlaceholder = (() => {
    if (precisaSelecionarGt) {
      return novoAlvoTipo === 'resposta'
        ? 'Selecione um GT para listar respostas'
        : 'Selecione um GT para listar os textos únicos';
    }
    if (carregandoAlvos) {
      return 'Carregando alvos...';
    }
    if (alvoOptions.length === 0) {
      return 'Nenhum registro encontrado para este filtro';
    }
    return 'Selecione um registro';
  })();

  const colecaoPlaceholder = (() => {
    if (colecaoFonteTipo === 'resposta' && isLoadingRespostas) {
      return 'Carregando respostas...';
    }
    if (colecaoFonteTipo === 'texto_unico' && isLoadingTodosTextoUnicos) {
      return 'Carregando textos únicos...';
    }
    if (colecaoOptions.length === 0) {
      return 'Nenhum conteúdo disponível para este filtro';
    }
    return 'Selecione um conteúdo para adicionar';
  })();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const alvoTipo = novoAlvoTipo.trim();
    const formato = novoFormato || 'pdf';
    if (alvoTipo === 'colecao') {
      if (colecaoItens.length === 0) {
        return;
      }
      const payloadJson = {
        titulo: colecaoTitulo || 'Documento personalizado',
        secoes: colecaoItens.map((item) => ({
          tipo: item.tipo,
          id: item.id,
          titulo: item.label,
        })),
      };
      await criarExportacao.mutateAsync({ alvoTipo, alvoId: 'colecao', formato, payloadJson });
      setColecaoItens([]);
      setColecaoAlvoId('');
      setColecaoTitulo('Documento personalizado');
      refetch();
      return;
    }
    const alvoId = Number(novoAlvoId);
    if (!alvoTipo || !alvoId) {
      return;
    }
    await criarExportacao.mutateAsync({ alvoTipo, alvoId, formato });
    setNovoAlvoId('');
    refetch();
  };

  const handleAdicionarColecao = () => {
    if (!colecaoAlvoId) return;
    const base = colecaoFonteTipo === 'resposta' ? respostaOptions : todosTextoUnicoOptions;
    const selecionado = base.find((item) => item.value === colecaoAlvoId);
    if (!selecionado) return;
    setColecaoItens((prev) => [
      ...prev,
      { id: Number(selecionado.value), tipo: colecaoFonteTipo, label: selecionado.label, gtId: selecionado.gtId },
    ]);
    setColecaoAlvoId('');
  };

  const handleMoverColecao = (index: number, direction: number) => {
    setColecaoItens((prev) => {
      const proximo = [...prev];
      const alvo = index + direction;
      if (alvo < 0 || alvo >= proximo.length) return prev;
      const [item] = proximo.splice(index, 1);
      proximo.splice(alvo, 0, item);
      return proximo;
    });
  };

  const handleRemoverColecao = (index: number) => {
    setColecaoItens((prev) => prev.filter((_, idx) => idx !== index));
  };

  const formatarAlvo = (job: ExportJob) => {
    if (job.alvo_tipo === 'colecao') {
      const payload = (job.payload_json ?? {}) as { secoes?: unknown; titulo?: unknown };
      const totalSecoes = Array.isArray(payload.secoes) ? payload.secoes.length : 0;
      const titulo = typeof payload.titulo === 'string' && payload.titulo ? payload.titulo : 'Coleção personalizada';
      return `${titulo} (${totalSecoes} bloco${totalSecoes === 1 ? '' : 's'})`;
    }
    if (job.alvo_tipo === 'resposta') {
      return `Resposta #${job.alvo_id}`;
    }
    if (job.alvo_tipo === 'texto_unico') {
      return `Texto único #${job.alvo_id}`;
    }
    if (job.alvo_tipo === 'quadro') {
      return `Perguntas (quadro) #${job.alvo_id}`;
    }
    return `${job.alvo_tipo} #${job.alvo_id}`;
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
            title: 'Use os seletores',
            description: 'Escolha o tipo e o conteúdo pelo nome — nada de decorar IDs.',
          },
          {
            title: 'Monte sequências',
            description: 'Adicione respostas ou textos únicos, ordene e gere um único documento.',
          },
          {
            title: 'Escolha o formato',
            description: 'PDF atende visualização rápida; DOCX facilita novas edições pelo time editorial.',
          },
        ]}
      />

      <div className="exportacoes__filters">
        <label>
          <span>Tipo de conteúdo</span>
          <select value={alvoTipoFiltro} onChange={(event) => setAlvoTipoFiltro(event.target.value)}>
            <option value="">Todos</option>
            {EXPORT_TARGETS.filter((item) => item.value !== 'colecao').map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>GT (opcional)</span>
          <select value={filtroGtId} onChange={(event) => setFiltroGtId(event.target.value)}>
            <option value="">Todos</option>
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>
        <label className="wide">
          <span>Conteúdo</span>
          <select value={alvoIdFiltro} onChange={(event) => setAlvoIdFiltro(event.target.value)}>
            <option value="">Todos os registros</option>
            {filtroAlvoOptions.map((item) => (
              <option key={`${item.value}-${item.label}`} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <small className="exportacoes__hint">Busque pelo nome e GT para encontrar rapidamente.</small>
        </label>
        <button type="button" className="ghost" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? 'Atualizando...' : 'Aplicar filtros'}
        </button>
      </div>

      <section className="exportacoes__nova">
        <h2>Nova exportação</h2>
        <form onSubmit={handleSubmit}>
          <label>
            <span>Tipo de exportação</span>
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
          {novoAlvoTipo === 'resposta' && (
            <label>
              <span>GT das respostas</span>
              <select
                value={respostaGtId === '' ? '' : String(respostaGtId)}
                onChange={(event) => setRespostaGtId(event.target.value ? Number(event.target.value) : '')}
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
              <small className="exportacoes__hint">Mostramos apenas respostas do GT escolhido.</small>
            </label>
          )}
          {novoAlvoTipo !== 'colecao' && (
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
          )}
          {novoAlvoTipo === 'colecao' && (
            <div className="exportacoes__colecao">
              <label className="full">
                <span>Título do documento</span>
                <input
                  type="text"
                  value={colecaoTitulo}
                  onChange={(event) => setColecaoTitulo(event.target.value)}
                  placeholder="Documento personalizado"
                />
              </label>
              <div className="exportacoes__colecao-grid">
                <label>
                  <span>GT para buscar conteúdo</span>
                  <select
                    value={colecaoGtId === '' ? '' : String(colecaoGtId)}
                    onChange={(event) => setColecaoGtId(event.target.value ? Number(event.target.value) : '')}
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
                </label>
                <label>
                  <span>Fonte</span>
                  <select
                    value={colecaoFonteTipo}
                    onChange={(event) => setColecaoFonteTipo(event.target.value as 'resposta' | 'texto_unico')}
                  >
                    <option value="resposta">Respostas</option>
                    <option value="texto_unico">Textos únicos</option>
                  </select>
                </label>
                <label className="full">
                  <span>Conteúdo</span>
                  <select
                    value={colecaoAlvoId}
                    onChange={(event) => setColecaoAlvoId(event.target.value)}
                    disabled={colecaoOptions.length === 0}
                  >
                    <option value="" disabled>
                      {colecaoPlaceholder}
                    </option>
                    {colecaoOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <small className="exportacoes__hint">Adicione vários itens e depois ordene a lista.</small>
                </label>
                <button
                  type="button"
                  className="exportacoes__add"
                  onClick={handleAdicionarColecao}
                  disabled={!colecaoAlvoId || colecaoOptions.length === 0}
                >
                  Adicionar à sequência
                </button>
              </div>
              <div className="exportacoes__colecao-list">
                {colecaoItens.length === 0 ? (
                  <p className="exportacoes__hint">
                    Nenhum item adicionado ainda. Busque um conteúdo e clique em &quot;Adicionar à sequência&quot;.
                  </p>
                ) : (
                  colecaoItens.map((item, index) => (
                    <div key={`${item.tipo}-${item.id}-${index}`} className="exportacoes__colecao-item">
                      <div>
                        <p className="exportacoes__colecao-eyebrow">
                          {item.tipo === 'resposta' ? 'Resposta' : 'Texto único'}
                        </p>
                        <strong>{item.label}</strong>
                      </div>
                      <div className="exportacoes__colecao-actions">
                        <button type="button" onClick={() => handleMoverColecao(index, -1)} aria-label="Mover para cima">
                          ↑
                        </button>
                        <button type="button" onClick={() => handleMoverColecao(index, 1)} aria-label="Mover para baixo">
                          ↓
                        </button>
                        <button type="button" onClick={() => handleRemoverColecao(index)} aria-label="Remover">
                          Remover
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
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
          <button
            type="submit"
            disabled={criarExportacao.isPending || (novoAlvoTipo === 'colecao' && colecaoItens.length === 0)}
          >
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
                  <td>{formatarAlvo(job)}</td>
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
