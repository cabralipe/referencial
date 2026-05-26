import { FormEvent, useMemo, useState } from 'react';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useAuth } from '@/context/AuthContext';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useBlocos, useCreateBloco, useCreateMidia, useMidias } from '@/hooks/useBiblioteca';
import { usePerguntas } from '@/hooks/usePerguntas';
import { useTarefas } from '@/hooks/useTarefas';

import './BibliotecaPage.css';

export function BibliotecaPage() {
  const { user } = useAuth();
  const [filtroPalavra, setFiltroPalavra] = useState('');
  const [filtroTags, setFiltroTags] = useState('');
  const [blocoError, setBlocoError] = useState<string | null>(null);
  const [midiaError, setMidiaError] = useState<string | null>(null);
  const [novoConteudo, setNovoConteudo] = useState('');
  const [gtSelecionadoId, setGtSelecionadoId] = useState<number | ''>('');
  const [tarefaSelecionadaId, setTarefaSelecionadaId] = useState<number | ''>('');
  const [perguntaSelecionadaId, setPerguntaSelecionadaId] = useState<number | ''>('');
  const [blocoSelecionadoId, setBlocoSelecionadoId] = useState<number | ''>('');
  const [midiaSelecionadaId, setMidiaSelecionadaId] = useState<number | ''>('');

  const gtId = typeof gtSelecionadoId === 'number' ? gtSelecionadoId : null;
  const tarefaId = typeof tarefaSelecionadaId === 'number' ? tarefaSelecionadaId : null;
  const perguntaId = typeof perguntaSelecionadaId === 'number' ? perguntaSelecionadaId : null;

  const tagsList = useMemo(
    () =>
      filtroTags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
    [filtroTags],
  );

  const { gtOptions } = useAvailableGts();
  const { data: tarefas } = useTarefas({ gtId: gtId ?? undefined, tipo: 'PERGUNTAS' });
  const { data: perguntas } = usePerguntas(tarefaId ?? undefined, gtId ?? undefined);
  const { data: midias, isLoading: midiasLoading } = useMidias({
    query: filtroPalavra || undefined,
    tags: tagsList,
    gtId,
    perguntaId,
  });
  const { data: blocos, isLoading: blocosLoading, refetch: refetchBlocos } = useBlocos({
    query: filtroPalavra || undefined,
    tags: tagsList,
    gtId,
    perguntaId,
  });
  const criarBloco = useCreateBloco();
  const criarMidia = useCreateMidia();
  const gtLookup = useMemo(() => new Map(gtOptions.map((gt) => [gt.id, gt.displayName])), [gtOptions]);
  const perguntasLookup = useMemo(
    () => new Map((perguntas ?? []).map((pergunta) => [pergunta.id, pergunta.texto])),
    [perguntas],
  );

  const blocoSelecionado = useMemo(() => {
    if (typeof blocoSelecionadoId !== 'number') {
      return null;
    }
    return (blocos ?? []).find((bloco) => bloco.id === blocoSelecionadoId) ?? null;
  }, [blocos, blocoSelecionadoId]);

  const midiaSelecionada = useMemo(() => {
    if (typeof midiaSelecionadaId !== 'number') {
      return null;
    }
    return (midias ?? []).find((midia) => midia.id === midiaSelecionadaId) ?? null;
  }, [midias, midiaSelecionadaId]);

  const isImageUrl = (url?: string | null) => {
    if (!url) return false;
    return /\.(png|jpe?g|gif|webp|svg)$/i.test(url);
  };

  const handleCriarBloco = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBlocoError(null);
    if (requiresGt && !gtId) {
      setBlocoError('Selecione um GT nos filtros para cadastrar referências.');
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const titulo = String(form.get('titulo') ?? '').trim();
    const conteudo = novoConteudo.trim();
    const tags = String(form.get('tags') ?? '')
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (!titulo || !conteudo) {
      return;
    }
    try {
      await criarBloco.mutateAsync({ titulo, conteudo_html: conteudo, tags, gt: gtId, pergunta: perguntaId });
      formElement.reset();
      setNovoConteudo('');
      refetchBlocos();
    } catch (error) {
      setBlocoError('Não foi possível salvar a referência. Verifique os dados e tente novamente.');
    }
  };

  const handleCriarMidia = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMidiaError(null);
    if (requiresGt && !gtId) {
      setMidiaError('Selecione um GT nos filtros para cadastrar links.');
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const titulo = String(form.get('titulo') ?? '').trim();
    const url = String(form.get('url') ?? '').trim();
    const descricao = String(form.get('descricao') ?? '').trim();
    const tags = String(form.get('tags') ?? '')
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (!titulo || !url) {
      return;
    }
    try {
      await criarMidia.mutateAsync({
        titulo,
        url,
        descricao: descricao || null,
        tags,
        gt: gtId,
        pergunta: perguntaId,
      });
      formElement.reset();
    } catch (error) {
      setMidiaError('Não foi possível salvar o link. Verifique o endereço e tente novamente.');
    }
  };

  const carregando = midiasLoading || blocosLoading;
  const requiresGt = user?.role !== 'admin_cliente' && user?.role !== 'super_admin';
  const canManageBiblioteca =
    user?.role === 'articulador' || user?.role === 'admin_cliente' || user?.role === 'super_admin';
  const handleChangeGt = (value: string) => {
    const selected = value ? Number(value) : '';
    setGtSelecionadoId(selected);
    setTarefaSelecionadaId('');
    setPerguntaSelecionadaId('');
  };
  const handleChangeTarefa = (value: string) => {
    const selected = value ? Number(value) : '';
    setTarefaSelecionadaId(selected);
    setPerguntaSelecionadaId('');
  };

  return (
    <div className="biblioteca">
      <header className="biblioteca__header">
        <div>
          <h1>Central bibliográfica</h1>
        </div>
      </header>

      <div className="biblioteca__filters">
        <label>
          <span>GT</span>
          <select
            value={gtSelecionadoId === '' ? '' : String(gtSelecionadoId)}
            onChange={(event) => handleChangeGt(event.target.value)}
          >
            <option value="">Todos os GTs disponíveis</option>
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Tarefa</span>
          <select
            value={tarefaSelecionadaId === '' ? '' : String(tarefaSelecionadaId)}
            onChange={(event) => handleChangeTarefa(event.target.value)}
            disabled={!tarefas || tarefas.length === 0}
          >
            <option value="">Todas as tarefas</option>
            {(tarefas ?? []).map((tarefa) => (
              <option key={tarefa.id} value={tarefa.id}>
                {tarefa.nome || `Tarefa #${tarefa.id}`}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Pergunta</span>
          <select
            value={perguntaSelecionadaId === '' ? '' : String(perguntaSelecionadaId)}
            onChange={(event) => setPerguntaSelecionadaId(event.target.value ? Number(event.target.value) : '')}
            disabled={!perguntas || perguntas.length === 0}
          >
            <option value="">Todas as perguntas</option>
            {(perguntas ?? []).map((pergunta) => (
              <option key={pergunta.id} value={pergunta.id}>
                {pergunta.ordem}. {pergunta.texto}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Busca textual</span>
          <input
            type="search"
            value={filtroPalavra}
            onChange={(event) => setFiltroPalavra(event.target.value)}
            placeholder="Ex.: alfabetização"
          />
        </label>
        <label>
          <span>Tags (vírgula)</span>
          <input
            type="text"
            value={filtroTags}
            onChange={(event) => setFiltroTags(event.target.value)}
            placeholder="Ex.: base,linguagens"
          />
        </label>
      </div>

      {canManageBiblioteca && (
        <>
          <section className="biblioteca__novo-bloco">
            <h2>Nova referência bibliográfica</h2>
            <p className="biblioteca__hint">
              Esta referência será vinculada ao GT e à pergunta selecionados nos filtros acima.
            </p>
            <form onSubmit={handleCriarBloco}>
              <label>
                <span>Título</span>
                <input name="titulo" type="text" placeholder="Ex.: Diretrizes para avaliação" required />
              </label>
              <label>
                <span>Tags</span>
                <input name="tags" type="text" placeholder="Ex.: base,competencias" />
              </label>
              <label className="full">
                <span>Referência (HTML ou texto)</span>
                <RichTextEditor
                  value={novoConteudo}
                  onChange={setNovoConteudo}
                  placeholder="Cole a referência, citação ou resumo"
                />
              </label>
          <button type="submit" disabled={criarBloco.isPending}>
            {criarBloco.isPending ? 'Salvando...' : 'Adicionar referência'}
          </button>
          {blocoError && <p className="biblioteca__error">{blocoError}</p>}
        </form>
      </section>

          <section className="biblioteca__novo-bloco">
            <h2>Novo link ou anexo</h2>
            <p className="biblioteca__hint">
              O link ficará disponível para os membros do GT selecionado nos filtros.
            </p>
            <form onSubmit={handleCriarMidia}>
              <label>
                <span>Título</span>
                <input name="titulo" type="text" placeholder="Ex.: Plano de estudo - capítulo 2" required />
              </label>
              <label>
                <span>URL do material</span>
                <input name="url" type="text" placeholder="Ex.: site.com/arquivo" required />
              </label>
              <label className="full">
                <span>Descrição</span>
                <textarea name="descricao" rows={3} placeholder="Contexto do material ou anexo" />
              </label>
              <label>
                <span>Tags</span>
                <input name="tags" type="text" placeholder="Ex.: leitura,avaliacao" />
              </label>
              <button type="submit" disabled={criarMidia.isPending}>
                {criarMidia.isPending ? 'Salvando...' : 'Adicionar link'}
              </button>
              {midiaError && <p className="biblioteca__error">{midiaError}</p>}
            </form>
          </section>
        </>
      )}

      {carregando ? (
        <FullPageLoader message="Buscando referências..." />
      ) : (
        <div className="biblioteca__grid">
          <section>
            <header>
              <h2>Referências textuais ({blocos?.length ?? 0})</h2>
            </header>
            <div className="biblioteca__selector">
              <label>
                <span>Selecionar referência</span>
                <select
                  value={blocoSelecionadoId === '' ? '' : String(blocoSelecionadoId)}
                  onChange={(event) =>
                    setBlocoSelecionadoId(event.target.value ? Number(event.target.value) : '')
                  }
                >
                  <option value="">Escolha uma referência para visualizar</option>
                  {(blocos ?? []).map((bloco) => (
                    <option key={bloco.id} value={bloco.id}>
                      {bloco.titulo}
                    </option>
                  ))}
                </select>
              </label>
              {blocoSelecionado && (
                <div className="biblioteca__preview">
                  <div className="biblioteca__preview-meta">
                    <strong>{blocoSelecionado.titulo}</strong>
                    <span>Atualizado em {new Date(blocoSelecionado.updated_at).toLocaleString('pt-BR')}</span>
                    {(blocoSelecionado.gt || blocoSelecionado.pergunta) && (
                      <ul className="biblioteca__meta">
                        {blocoSelecionado.gt && <li>GT: {gtLookup.get(blocoSelecionado.gt) ?? `GT #${blocoSelecionado.gt}`}</li>}
                        {blocoSelecionado.pergunta && (
                          <li>
                            Pergunta:{' '}
                            {perguntasLookup.get(blocoSelecionado.pergunta) ?? `Pergunta #${blocoSelecionado.pergunta}`}
                          </li>
                        )}
                      </ul>
                    )}
                    {blocoSelecionado.tags && blocoSelecionado.tags.length > 0 && (
                      <ul className="biblioteca__tags">
                        {blocoSelecionado.tags.map((tag) => (
                          <li key={tag}>#{tag}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div
                    className="biblioteca__preview-html"
                    dangerouslySetInnerHTML={{ __html: blocoSelecionado.conteudo_html }}
                  />
                </div>
              )}
            </div>
            {blocos && blocos.length > 0 ? (
              <div className="biblioteca__cards">
                {blocos.map((bloco) => (
                  <article key={bloco.id} className="biblioteca__card">
                    <header>
                      <div>
                        <h3>{bloco.titulo}</h3>
                        <span>Atualizado em {new Date(bloco.updated_at).toLocaleString('pt-BR')}</span>
                        {(bloco.gt || bloco.pergunta) && (
                          <ul className="biblioteca__meta">
                            {bloco.gt && <li>GT: {gtLookup.get(bloco.gt) ?? `GT #${bloco.gt}`}</li>}
                            {bloco.pergunta && (
                              <li>
                                Pergunta: {perguntasLookup.get(bloco.pergunta) ?? `Pergunta #${bloco.pergunta}`}
                              </li>
                            )}
                          </ul>
                        )}
                      </div>
                      {bloco.tags && bloco.tags.length > 0 && (
                        <ul className="biblioteca__tags">
                          {bloco.tags.map((tag) => (
                            <li key={tag}>#{tag}</li>
                          ))}
                        </ul>
                      )}
                    </header>

                    <div
                      className="biblioteca__preview-html"
                      dangerouslySetInnerHTML={{ __html: bloco.conteudo_html }}
                    />
                  </article>
                ))}
              </div>
            ) : (
              <div className="biblioteca__empty">
                <p>Nenhuma referência encontrada com os filtros atuais.</p>
              </div>
            )}
          </section>

          <section className="biblioteca__links">
            <header>
              <h2>Links e anexos ({midias?.length ?? 0})</h2>
            </header>
            <div className="biblioteca__selector">
              <label>
                <span>Selecionar link</span>
                <select
                  value={midiaSelecionadaId === '' ? '' : String(midiaSelecionadaId)}
                  onChange={(event) =>
                    setMidiaSelecionadaId(event.target.value ? Number(event.target.value) : '')
                  }
                >
                  <option value="">Escolha um link para visualizar</option>
                  {(midias ?? []).map((midia) => (
                    <option key={midia.id} value={midia.id}>
                      {midia.titulo || midia.descricao || midia.url}
                    </option>
                  ))}
                </select>
              </label>
              {midiaSelecionada && (
                <div className="biblioteca__preview biblioteca__preview--media">
                  <div className="biblioteca__preview-meta">
                    <strong>{midiaSelecionada.titulo || `Mídia #${midiaSelecionada.id}`}</strong>
                    <div className="biblioteca__midia-primary">
                      <a className="biblioteca__midia-open" href={midiaSelecionada.url} target="_blank" rel="noreferrer">
                        Abrir link/anexo
                      </a>
                      <span className="biblioteca__midia-url">{midiaSelecionada.url}</span>
                    </div>
                    <span>Registrada em {new Date(midiaSelecionada.created_at).toLocaleString('pt-BR')}</span>
                    {(midiaSelecionada.gt || midiaSelecionada.pergunta) && (
                      <ul className="biblioteca__meta">
                        {midiaSelecionada.gt && (
                          <li>GT: {gtLookup.get(midiaSelecionada.gt) ?? `GT #${midiaSelecionada.gt}`}</li>
                        )}
                        {midiaSelecionada.pergunta && (
                          <li>
                            Pergunta:{' '}
                            {perguntasLookup.get(midiaSelecionada.pergunta) ?? `Pergunta #${midiaSelecionada.pergunta}`}
                          </li>
                        )}
                      </ul>
                    )}
                    {midiaSelecionada.tags && midiaSelecionada.tags.length > 0 && (
                      <ul className="biblioteca__tags">
                        {midiaSelecionada.tags.map((tag) => (
                          <li key={tag}>#{tag}</li>
                        ))}
                      </ul>
                    )}
                    {midiaSelecionada.descricao && (
                      <p className="biblioteca__midia-descricao">{midiaSelecionada.descricao}</p>
                    )}
                  </div>
                  {isImageUrl(midiaSelecionada.url) && (
                    <img
                      className="biblioteca__thumb"
                      src={midiaSelecionada.url}
                      alt={midiaSelecionada.titulo || 'Mídia'}
                    />
                  )}
                </div>
              )}
            </div>
            {midias && midias.length > 0 ? (
              <ul className="biblioteca__midias">
                {midias.map((midia) => (
                  <li key={midia.id}>
                    <div className="biblioteca__midia-card">
                      <div className="biblioteca__midia-card-top">
                        <div>
                          <strong>{midia.titulo || midia.url}</strong>
                          {midia.descricao && <p>{midia.descricao}</p>}
                        </div>
                        <a className="biblioteca__midia-open" href={midia.url} target="_blank" rel="noreferrer">
                          Abrir link/anexo
                        </a>
                      </div>
                      <span className="biblioteca__midia-url">{midia.url}</span>
                      <span>Registrada em {new Date(midia.created_at).toLocaleString('pt-BR')}</span>
                      {(midia.gt || midia.pergunta) && (
                        <ul className="biblioteca__meta">
                          {midia.gt && <li>GT: {gtLookup.get(midia.gt) ?? `GT #${midia.gt}`}</li>}
                          {midia.pergunta && (
                            <li>Pergunta: {perguntasLookup.get(midia.pergunta) ?? `Pergunta #${midia.pergunta}`}</li>
                          )}
                        </ul>
                      )}
                      {midia.tags && midia.tags.length > 0 && (
                        <ul className="biblioteca__tags">
                          {midia.tags.map((tag) => (
                            <li key={tag}>#{tag}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="biblioteca__empty">
                <p>Nenhum link encontrado. Ajuste os filtros ou cadastre um novo material.</p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
