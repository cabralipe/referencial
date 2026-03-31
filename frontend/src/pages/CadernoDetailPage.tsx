import { FormEvent, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import { Card } from '@/components/common/Card';
import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useBlocos, useCreateBloco, useUpdateBloco } from '@/hooks/useBiblioteca';
import { useTarefas } from '@/hooks/useTarefas';
import { usePerguntas } from '@/hooks/usePerguntas';

import './CadernoDetailPage.css';

export function CadernoDetailPage() {
  const { id = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { gtOptions } = useAvailableGts();
  const selectedGtId = searchParams.get('gt') ? Number(searchParams.get('gt')) : gtOptions[0]?.id ?? null;

  const { data: blocos, isLoading } = useBlocos({ tags: [`caderno:${id}`], gtId: selectedGtId ?? undefined });
  const createBloco = useCreateBloco();
  const updateBloco = useUpdateBloco();

  const { data: tarefas } = useTarefas({ tipo: 'PERGUNTAS', gtId: selectedGtId ?? undefined });
  const [selectedTarefaId, setSelectedTarefaId] = useState<number | ''>('');
  const { data: perguntas } = usePerguntas(
    typeof selectedTarefaId === 'number' ? selectedTarefaId : undefined,
    selectedGtId ?? undefined,
  );
  const [selectedPerguntaId, setSelectedPerguntaId] = useState<number | ''>('');

  const [titulo, setTitulo] = useState('');
  const [conteudo, setConteudo] = useState('');
  const [feedback, setFeedback] = useState('');

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingTitulo, setEditingTitulo] = useState('');
  const [editingConteudo, setEditingConteudo] = useState('');
  const blocoEditando = useMemo(() => (blocos ?? []).find((bloco) => bloco.id === editingId) ?? null, [blocos, editingId]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    setFeedback('');
    if (!selectedGtId) {
      setFeedback('Selecione um GT antes de adicionar textos.');
      return;
    }
    if (!titulo.trim() || !conteudo.trim()) {
      setFeedback('Preencha título e conteúdo.');
      return;
    }
    try {
      await createBloco.mutateAsync({
        titulo,
        conteudo_html: conteudo,
        tags: [`caderno:${id}`],
        gt: selectedGtId,
        pergunta: typeof selectedPerguntaId === 'number' ? selectedPerguntaId : undefined,
      });
      setTitulo('');
      setConteudo('');
    } catch (error) {
      setFeedback('Não foi possível salvar o texto.');
    }
  };

  const handleUpdate = async () => {
    if (!blocoEditando) return;
    try {
      await updateBloco.mutateAsync({
        blocoId: blocoEditando.id,
        titulo: editingTitulo,
        conteudo_html: editingConteudo,
        tags: blocoEditando.tags ?? [],
        gt: blocoEditando.gt ?? undefined,
        pergunta: blocoEditando.pergunta ?? undefined,
        etag: blocoEditando.etag,
      });
      setEditingId(null);
    } catch (error) {
      setFeedback('Não foi possível atualizar o texto.');
    }
  };

  if (isLoading) {
    return <FullPageLoader message="Carregando caderno..." />;
  }

  return (
    <div className="caderno-detail">
      <PageHeader
        title={`Caderno ${id.replace(/-/g, ' ')}`}
        description="Edite e organize os textos deste caderno."
      />

      <Card>
        <form className="caderno-detail__form" onSubmit={handleCreate}>
          <h2>Novo texto</h2>
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
            <span>Tarefa (opcional)</span>
            <select
              value={selectedTarefaId === '' ? '' : String(selectedTarefaId)}
              onChange={(event) => {
                const value = event.target.value ? Number(event.target.value) : '';
                setSelectedTarefaId(value);
                setSelectedPerguntaId('');
              }}
            >
              <option value="">Nenhuma</option>
              {(tarefas ?? []).map((tarefa) => (
                <option key={tarefa.id} value={tarefa.id}>
                  {tarefa.nome || `Tarefa #${tarefa.id}`}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Pergunta (opcional)</span>
            <select
              value={selectedPerguntaId === '' ? '' : String(selectedPerguntaId)}
              onChange={(event) => setSelectedPerguntaId(event.target.value ? Number(event.target.value) : '')}
              disabled={!perguntas?.length}
            >
              <option value="">Nenhuma</option>
              {(perguntas ?? []).map((pergunta) => (
                <option key={pergunta.id} value={pergunta.id}>
                  {pergunta.ordem}. {pergunta.texto}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Título</span>
            <input value={titulo} onChange={(event) => setTitulo(event.target.value)} />
          </label>
          <label className="full">
            <span>Conteúdo</span>
            <RichTextEditor value={conteudo} onChange={setConteudo} placeholder="Escreva o conteúdo." />
          </label>
          <Button variant="secondary" type="submit" disabled={createBloco.isPending}>
            {createBloco.isPending ? 'Salvando...' : 'Adicionar texto'}
          </Button>
          {feedback && <p className="caderno-detail__feedback">{feedback}</p>}
        </form>
      </Card>

      <div className="caderno-detail__lista">
        {(blocos ?? []).map((bloco) => (
          <Card key={bloco.id}>
            <div className="caderno-detail__item">
              <header>
                <h3>{bloco.titulo}</h3>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditingId(bloco.id);
                    setEditingTitulo(bloco.titulo);
                    setEditingConteudo(bloco.conteudo_html);
                  }}
                >
                  Editar
                </Button>
              </header>
              <div dangerouslySetInnerHTML={{ __html: bloco.conteudo_html }} />
              {bloco.pergunta && <small>Vinculado à pergunta #{bloco.pergunta}</small>}
            </div>
          </Card>
        ))}
        {(blocos ?? []).length === 0 && <p className="caderno-detail__feedback">Nenhum texto neste caderno.</p>}
      </div>

      {blocoEditando && (
        <Card>
          <div className="caderno-detail__editor">
            <h2>Editar texto</h2>
            <label>
              <span>Título</span>
              <input
                value={editingTitulo}
                onChange={(event) => setEditingTitulo(event.target.value)}
              />
            </label>
            <label className="full">
              <span>Conteúdo</span>
              <RichTextEditor value={editingConteudo} onChange={setEditingConteudo} placeholder="Atualize o conteúdo." />
            </label>
            <div className="caderno-detail__editor-actions">
              <Button variant="secondary" onClick={handleUpdate} disabled={updateBloco.isPending}>
                {updateBloco.isPending ? 'Atualizando...' : 'Salvar alterações'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setEditingId(null);
                  setEditingTitulo('');
                  setEditingConteudo('');
                }}
              >
                Cancelar
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
