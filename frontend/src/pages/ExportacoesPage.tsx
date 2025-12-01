import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateExportJob, useExportJobs } from '@/hooks/useExportJobs';

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
  const [novoAlvoId, setNovoAlvoId] = useState('');
  const [novoFormato, setNovoFormato] = useState(FORMATS[0]);

  const { data: exportsJobs, isLoading, refetch, isFetching } = useExportJobs({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdFiltro ? Number(alvoIdFiltro) : undefined,
  });
  const criarExportacao = useCreateExportJob();

  const sugestoesIds = useMemo(() => {
    if (!exportsJobs || !novoAlvoTipo) return [];
    const ids = exportsJobs
      .filter((job) => job.alvo_tipo === novoAlvoTipo)
      .map((job) => job.alvo_id)
      .filter((value, index, arr) => arr.indexOf(value) === index)
      .slice(0, 6);
    return ids;
  }, [exportsJobs, novoAlvoTipo]);

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
            description: 'Informe o tipo de entidade (ex.: texto_unico, tarefa) e o ID correspondente.',
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
          <label>
            <span>Alvo ID</span>
            <input
              name="alvoId"
              type="number"
              min={1}
              placeholder="Ex.: 12"
              required
              value={novoAlvoId}
              onChange={(e) => setNovoAlvoId(e.target.value)}
            />
            <small className="exportacoes__hint">
              Use o ID exibido na listagem do alvo (ex.: Texto único #12). Selecione um sugerido abaixo para preencher.
            </small>
            {sugestoesIds.length > 0 && (
              <div className="exportacoes__suggestions">
                {sugestoesIds.map((id) => (
                  <button key={id} type="button" onClick={() => setNovoAlvoId(String(id))}>
                    #{id}
                  </button>
                ))}
              </div>
            )}
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
