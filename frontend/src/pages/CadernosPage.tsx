import { FormEvent, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { Card } from '@/components/common/Card';
import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/common/Button';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useBlocos, useCreateBloco } from '@/hooks/useBiblioteca';

import './CadernosPage.css';

const slugify = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');

export function CadernosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { gtOptions } = useAvailableGts();
  const selectedGtId = searchParams.get('gt') ? Number(searchParams.get('gt')) : gtOptions[0]?.id ?? null;
  const { data: blocos, isLoading } = useBlocos({ gtId: selectedGtId ?? undefined });
  const createBloco = useCreateBloco();

  const [nomeCaderno, setNomeCaderno] = useState('');
  const [tituloTexto, setTituloTexto] = useState('');
  const [conteudoTexto, setConteudoTexto] = useState('');
  const [feedback, setFeedback] = useState('');

  const cadernos = useMemo(() => {
    const map = new Map<string, { id: string; nome: string; count: number }>();
    (blocos ?? []).forEach((bloco) => {
      const tag = (bloco.tags ?? []).find((item) => item.startsWith('caderno:'));
      if (!tag) return;
      const id = tag.replace('caderno:', '');
      const nome = tag.replace('caderno:', '').replace(/-/g, ' ');
      const entry = map.get(id) ?? { id, nome, count: 0 };
      entry.count += 1;
      map.set(id, entry);
    });
    return Array.from(map.values()).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
  }, [blocos]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    setFeedback('');
    if (!selectedGtId) {
      setFeedback('Selecione um GT antes de criar o caderno.');
      return;
    }
    const slug = slugify(nomeCaderno);
    if (!slug) {
      setFeedback('Informe um nome válido para o caderno.');
      return;
    }
    try {
      await createBloco.mutateAsync({
        titulo: tituloTexto || `Texto inicial - ${nomeCaderno}`,
        conteudo_html: conteudoTexto || '<p>Comece a escrever aqui.</p>',
        tags: [`caderno:${slug}`],
        gt: selectedGtId,
      });
      setNomeCaderno('');
      setTituloTexto('');
      setConteudoTexto('');
    } catch (error) {
      setFeedback('Não foi possível criar o caderno.');
    }
  };

  if (isLoading) {
    return <FullPageLoader message="Carregando cadernos..." />;
  }

  return (
    <div className="cadernos">
      <PageHeader
        title="Cadernos"
        description="Organize textos por temas e reutilize-os nas trilhas e no PPP."
      />

      <Card>
        <form className="cadernos__form" onSubmit={handleCreate}>
          <h2>Novo caderno</h2>
          <label>
            <span>GT</span>
            <select
              value={selectedGtId ?? ''}
              onChange={(event) => {
                const value = event.target.value ? Number(event.target.value) : null;
                if (value) {
                  setSearchParams({ gt: String(value) });
                } else {
                  setSearchParams({});
                }
              }}
            >
              {gtOptions.map((gt) => (
                <option key={gt.id} value={gt.id}>
                  {gt.displayName}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Nome do caderno</span>
            <input value={nomeCaderno} onChange={(event) => setNomeCaderno(event.target.value)} />
          </label>
          <label>
            <span>Título do texto inicial</span>
            <input value={tituloTexto} onChange={(event) => setTituloTexto(event.target.value)} />
          </label>
          <label className="full">
            <span>Texto inicial</span>
            <RichTextEditor value={conteudoTexto} onChange={setConteudoTexto} placeholder="Escreva o texto inicial." />
          </label>
          <Button variant="secondary" type="submit" disabled={createBloco.isPending}>
            {createBloco.isPending ? 'Criando...' : 'Criar caderno'}
          </Button>
          {feedback && <p className="cadernos__feedback">{feedback}</p>}
        </form>
      </Card>

      <div className="cadernos__grid">
        {cadernos.map((caderno) => (
          <Card key={caderno.id}>
            <div className="cadernos__card">
              <div>
                <h3>{caderno.nome}</h3>
                <p>{caderno.count} texto(s)</p>
              </div>
              <Link to={`/cadernos/${caderno.id}?gt=${selectedGtId ?? ''}`}>
                <Button size="sm" variant="primary">Abrir</Button>
              </Link>
            </div>
          </Card>
        ))}
        {cadernos.length === 0 && (
          <p className="cadernos__empty">Nenhum caderno criado ainda.</p>
        )}
      </div>
    </div>
  );
}
