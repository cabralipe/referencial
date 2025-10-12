import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useBlocos, useCreateBloco, useMidias, useUpdateBloco } from '@/hooks/useBiblioteca';

import './BibliotecaPage.css';

export function BibliotecaPage() {
  const [filtroPalavra, setFiltroPalavra] = useState('');
  const [filtroTags, setFiltroTags] = useState('');

  const tagsList = useMemo(
    () =>
      filtroTags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
    [filtroTags],
  );

  const { data: midias, isLoading: midiasLoading } = useMidias({ query: filtroPalavra || undefined, tags: tagsList });
  const { data: blocos, isLoading: blocosLoading, refetch: refetchBlocos } = useBlocos({
    query: filtroPalavra || undefined,
    tags: tagsList,
  });
  const criarBloco = useCreateBloco();
  const atualizarBloco = useUpdateBloco();

  const [draftBlocos, setDraftBlocos] = useState<Record<number, string>>({});

  const handleCriarBloco = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const titulo = String(form.get('titulo') ?? '').trim();
    const conteudo = String(form.get('conteudo') ?? '').trim();
    const tags = String(form.get('tags') ?? '')
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (!titulo || !conteudo) {
      return;
    }
    await criarBloco.mutateAsync({ titulo, conteudo_html: conteudo, tags });
    event.currentTarget.reset();
    refetchBlocos();
  };

  const handleAtualizarBloco = async (id: number, etag: string, tags: string[] | null) => {
    await atualizarBloco.mutateAsync({
      blocoId: id,
      conteudo_html: draftBlocos[id],
      etag,
      tags,
    });
    refetchBlocos();
  };

  const carregando = midiasLoading || blocosLoading;

  return (
    <div className="biblioteca">
      <header className="biblioteca__header">
        <div>
          <h1>Biblioteca de Apoio</h1>
          <p>Armazene blocos reutilizáveis e mídias para enriquecer os referenciais curriculares.</p>
        </div>
      </header>

      <PageInstructions
        title="Como aproveitar a biblioteca"
        description="Centralize textos e links para acelerar a construção do material final."
        items={[
          {
            title: 'Filtre por tags',
            description: 'Combine palavras-chave com hashtags para encontrar blocos específicos.',
          },
          {
            title: 'Reaproveite conteúdo',
            description: 'Copie o HTML de blocos validados e cole diretamente nas respostas dos GTs.',
          },
          {
            title: 'Mantenha versões',
            description: 'Atualize blocos existentes para preservar histórico e manter consistência.',
          },
        ]}
      />

      <div className="biblioteca__filters">
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

      <section className="biblioteca__novo-bloco">
        <h2>Novo bloco reutilizável</h2>
        <form onSubmit={handleCriarBloco}>
          <label>
            <span>Título</span>
            <input name="titulo" type="text" placeholder="Ex.: Princípios gerais" required />
          </label>
          <label>
            <span>Tags</span>
            <input name="tags" type="text" placeholder="Ex.: base,competencias" />
          </label>
          <label className="full">
            <span>Conteúdo HTML</span>
            <textarea name="conteudo" rows={4} placeholder="Cole o conteúdo em HTML" required />
          </label>
          <button type="submit" disabled={criarBloco.isPending}>
            {criarBloco.isPending ? 'Salvando...' : 'Adicionar bloco'}
          </button>
        </form>
      </section>

      {carregando ? (
        <FullPageLoader message="Buscando itens da biblioteca..." />
      ) : (
        <div className="biblioteca__grid">
          <section>
            <header>
              <h2>Blocos de texto ({blocos?.length ?? 0})</h2>
            </header>
            {blocos && blocos.length > 0 ? (
              <div className="biblioteca__cards">
                {blocos.map((bloco) => (
                  <article key={bloco.id} className="biblioteca__card">
                    <header>
                      <div>
                        <h3>{bloco.titulo}</h3>
                        <span>Atualizado em {new Date(bloco.updated_at).toLocaleString('pt-BR')}</span>
                      </div>
                      {bloco.tags && bloco.tags.length > 0 && (
                        <ul className="biblioteca__tags">
                          {bloco.tags.map((tag) => (
                            <li key={tag}>#{tag}</li>
                          ))}
                        </ul>
                      )}
                    </header>

                    <details>
                      <summary>Visualizar HTML</summary>
                      <div dangerouslySetInnerHTML={{ __html: bloco.conteudo_html }} />
                    </details>

                    <label className="biblioteca__editar">
                      <span>Atualizar conteúdo</span>
                      <textarea
                        rows={3}
                        value={draftBlocos[bloco.id] ?? bloco.conteudo_html}
                        onChange={(event) => setDraftBlocos((prev) => ({ ...prev, [bloco.id]: event.target.value }))}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => handleAtualizarBloco(bloco.id, bloco.etag, bloco.tags)}
                      disabled={atualizarBloco.isPending}
                    >
                      {atualizarBloco.isPending ? 'Salvando...' : 'Salvar alteração'}
                    </button>
                  </article>
                ))}
              </div>
            ) : (
              <div className="biblioteca__empty">
                <p>Nenhum bloco encontrado com os filtros atuais.</p>
              </div>
            )}
          </section>

          <section>
            <header>
              <h2>Mídias cadastradas ({midias?.length ?? 0})</h2>
            </header>
            {midias && midias.length > 0 ? (
              <ul className="biblioteca__midias">
                {midias.map((midia) => (
                  <li key={midia.id}>
                    <div>
                      <strong>{midia.url}</strong>
                      <span>Registrada em {new Date(midia.created_at).toLocaleString('pt-BR')}</span>
                      {midia.legenda && <p>{midia.legenda}</p>}
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
                <p>Nenhuma mídia encontrada. Ajuste os filtros ou realize uploads via API.</p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
