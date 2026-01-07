import { FormEvent, useEffect, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import {
  useCamposFormulario,
  useCreateCampoFormulario,
  useCreateFormulario,
  useFormularios,
  useSubmitFormulario,
} from '@/hooks/useFormularios';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useAuth } from '@/context/AuthContext';

import './FormulariosPage.css';

type ValorCampo = string | number | boolean | null;

type CampoDraft = {
  chave: string;
  tipo: string;
  obrigatorio: boolean;
  ordem: number;
  configJson: string;
};

const FIELD_TYPES = [
  { value: 'texto', label: 'Texto' },
  { value: 'select', label: 'Seleção' },
  { value: 'upload', label: 'Upload' },
  { value: 'inteiro', label: 'Inteiro' },
  { value: 'decimal', label: 'Decimal' },
  { value: 'bool', label: 'Booleano' },
];

export function FormulariosPage() {
  const { data: formularios, isLoading, refetch } = useFormularios();
  const [selectedFormulario, setSelectedFormulario] = useState<number | null>(null);
  const [ownerType, setOwnerType] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [gtDestino, setGtDestino] = useState<number | ''>('');
  const [values, setValues] = useState<Record<number, ValorCampo>>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [createFeedback, setCreateFeedback] = useState<string | null>(null);
  const [novoNome, setNovoNome] = useState('');
  const [novoDescricao, setNovoDescricao] = useState('');
  const [novoAtivo, setNovoAtivo] = useState(true);
  const [camposDraft, setCamposDraft] = useState<CampoDraft[]>([]);

  const { data: campos, isFetching: camposLoading } = useCamposFormulario(selectedFormulario ?? undefined);
  const submitFormulario = useSubmitFormulario();
  const createFormulario = useCreateFormulario();
  const createCampo = useCreateCampoFormulario();
  const { gtOptions } = useAvailableGts({ scope: 'member' });
  const { user } = useAuth();

  const canCreate =
    user?.role === 'admin_cliente' ||
    user?.role === 'super_admin' ||
    user?.role === 'articulador' ||
    user?.role === 'membro_gt';

  const formularioSelecionado = useMemo(
    () => formularios?.find((item) => item.id === selectedFormulario) ?? null,
    [formularios, selectedFormulario],
  );

  useEffect(() => {
    if (typeof gtDestino === 'number') {
      setOwnerType('gt');
      setOwnerId(String(gtDestino));
    }
  }, [gtDestino]);

  const handleChange = (campoId: number, valor: ValorCampo) => {
    setValues((prev) => ({
      ...prev,
      [campoId]: valor,
    }));
  };

  const handleAddCampo = () => {
    setCamposDraft((prev) => [
      ...prev,
      {
        chave: '',
        tipo: 'texto',
        obrigatorio: false,
        ordem: prev.length + 1,
        configJson: '',
      },
    ]);
  };

  const handleUpdateCampo = (index: number, patch: Partial<CampoDraft>) => {
    setCamposDraft((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  };

  const handleRemoveCampo = (index: number) => {
    setCamposDraft((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCreateFormulario = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateFeedback(null);
    if (!novoNome.trim()) {
      setCreateFeedback('Informe o nome do formulário.');
      return;
    }
    if (camposDraft.length === 0) {
      setCreateFeedback('Adicione ao menos um campo.');
      return;
    }
    const camposValidos = camposDraft.every((campo) => campo.chave.trim() && campo.tipo.trim());
    if (!camposValidos) {
      setCreateFeedback('Preencha chave e tipo para todos os campos.');
      return;
    }
    try {
      const formulario = await createFormulario.mutateAsync({
        nome: novoNome.trim(),
        descricao: novoDescricao.trim() || undefined,
        ativo: novoAtivo,
      });
      for (const campo of camposDraft) {
        let configJson: Record<string, unknown> | undefined;
        if (campo.configJson.trim()) {
          configJson = JSON.parse(campo.configJson);
        }
        await createCampo.mutateAsync({
          formularioId: formulario.id,
          chave: campo.chave.trim(),
          tipo: campo.tipo,
          obrigatorio: campo.obrigatorio,
          ordem: campo.ordem,
          ...(configJson ? { config_json: configJson } : {}),
        });
      }
      setCreateFeedback('Formulário criado e disponível para envio.');
      setNovoNome('');
      setNovoDescricao('');
      setNovoAtivo(true);
      setCamposDraft([]);
      refetch();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Não foi possível criar o formulário.';
      setCreateFeedback(message);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
    if (!selectedFormulario || !campos) {
      return;
    }

    const respostas = campos.map((campo) => ({
      campo,
      valor: values[campo.id] ?? null,
    }));
    try {
      await submitFormulario.mutateAsync({
        formularioId: selectedFormulario,
        respostas,
        ownerId: ownerId ? Number(ownerId) : undefined,
        ownerType: ownerType || undefined,
      });
      setFeedback('Respostas enviadas com sucesso.');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Não foi possível enviar as respostas.';
      setFeedback(message);
    }
  };

  if (isLoading && !formularios) {
    return <FullPageLoader message="Carregando formulários..." />;
  }

  return (
    <div className="formularios">
      <header className="formularios__header">
        <div>
          <h1>Formulários Dinâmicos</h1>
          <p>Responda levantamentos customizados e registre evidências atreladas aos GTs.</p>
        </div>
      </header>

      <PageInstructions
        title="Como preencher corretamente"
        description="Os formulários dinâmicos mudam conforme o cliente; confira obrigatoriedades antes de enviar."
        items={[
          {
            title: 'Escolha o formulário',
            description: 'Selecione o item na lista para visualizar os campos configurados pela administração.',
          },
          {
            title: 'Preencha com precisão',
            description: 'Tipos de campo definem o formato aceito. Valores inconsistentes serão descartados.',
          },
          {
            title: 'Informe o contexto',
            description: 'Owner (tipo e ID) vincula a resposta a um GT, tarefa ou registro específico.',
          },
        ]}
      />

      <div className="formularios__layout">
        <aside>
          <h2>Disponíveis ({formularios?.length ?? 0})</h2>
          <ul>
            {(formularios ?? []).map((form) => (
              <li key={form.id}>
                <button
                  type="button"
                  className={selectedFormulario === form.id ? 'active' : ''}
                  onClick={() => setSelectedFormulario(form.id)}
                >
                  <strong>{form.nome}</strong>
                  <span>{form.descricao}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="formularios__main">
          {camposLoading && !campos ? (
            <FullPageLoader message="Carregando campos..." />
          ) : formularioSelecionado && campos ? (
            <form onSubmit={handleSubmit} className="formularios__form">
              <div className="formularios__contexto">
                <label>
                  <span>Enviar para GT</span>
                  <select
                    value={gtDestino === '' ? '' : String(gtDestino)}
                    onChange={(event) => setGtDestino(event.target.value ? Number(event.target.value) : '')}
                  >
                    <option value="">Selecione um GT</option>
                    {gtOptions.map((gt) => (
                      <option key={gt.id} value={gt.id}>
                        {gt.displayName}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Owner type</span>
                  <input
                    type="text"
                    value={ownerType}
                    onChange={(event) => setOwnerType(event.target.value)}
                    placeholder="Ex.: tarefa"
                    disabled={typeof gtDestino === 'number'}
                  />
                </label>
                <label>
                  <span>Owner ID</span>
                  <input
                    type="number"
                    value={ownerId}
                    onChange={(event) => setOwnerId(event.target.value)}
                    placeholder="Ex.: 12"
                    disabled={typeof gtDestino === 'number'}
                  />
                </label>
              </div>

              {campos.map((campo) => {
                const tipo = campo.tipo.toLowerCase();
                const valor = values[campo.id] ?? '';
                const obrigatorio = campo.obrigatorio;

                if (tipo.includes('bool')) {
                  return (
                    <label key={campo.id} className="formularios__campo">
                      <span>
                        {campo.chave}
                        {obrigatorio ? <em> obrigatório</em> : null}
                      </span>
                      <select
                        value={valor === '' ? '' : valor === true ? 'true' : 'false'}
                        onChange={(event) => handleChange(campo.id, event.target.value === 'true')}
                        required={obrigatorio}
                      >
                        <option value="">Selecione</option>
                        <option value="true">Sim</option>
                        <option value="false">Não</option>
                      </select>
                    </label>
                  );
                }

                if (tipo.includes('num')) {
                  return (
                    <label key={campo.id} className="formularios__campo">
                      <span>
                        {campo.chave}
                        {obrigatorio ? <em> obrigatório</em> : null}
                      </span>
                      <input
                        type="number"
                        value={valor ?? ''}
                        onChange={(event) => handleChange(campo.id, event.target.value)}
                        required={obrigatorio}
                      />
                    </label>
                  );
                }

                return (
                  <label key={campo.id} className="formularios__campo">
                    <span>
                      {campo.chave}
                      {obrigatorio ? <em> obrigatório</em> : null}
                    </span>
                    <textarea
                      value={valor as string}
                      onChange={(event) => handleChange(campo.id, event.target.value)}
                      rows={4}
                      required={obrigatorio}
                    />
                  </label>
                );
              })}

              {feedback && <p className="formularios__feedback">{feedback}</p>}

              <div className="formularios__actions">
                <button type="submit" disabled={submitFormulario.isPending}>
                  {submitFormulario.isPending ? 'Enviando...' : 'Enviar respostas'}
                </button>
              </div>
            </form>
          ) : (
            <div className="formularios__empty">
              <h3>Selecione um formulário</h3>
              <p>Escolha um item na lista ao lado para visualizar e preencher os campos.</p>
            </div>
          )}
        </section>
      </div>

      {canCreate && (
        <section className="formularios__criar">
          <header>
            <h2>Criar formulário dinâmico</h2>
            <p>Defina campos e publique rapidamente para os GTs.</p>
          </header>
          <form onSubmit={handleCreateFormulario}>
            <label>
              <span>Nome</span>
              <input value={novoNome} onChange={(event) => setNovoNome(event.target.value)} />
            </label>
            <label>
              <span>Descrição</span>
              <input value={novoDescricao} onChange={(event) => setNovoDescricao(event.target.value)} />
            </label>
            <label>
              <span>Ativo</span>
              <select value={novoAtivo ? 'true' : 'false'} onChange={(event) => setNovoAtivo(event.target.value === 'true')}>
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </label>

            <div className="formularios__campos">
              <div className="formularios__campos-header">
                <strong>Campos</strong>
                <button type="button" onClick={handleAddCampo}>
                  Adicionar campo
                </button>
              </div>
              {camposDraft.length === 0 ? (
                <p className="formularios__campos-empty">Adicione campos para compor o formulário.</p>
              ) : (
                camposDraft.map((campo, index) => (
                  <div key={`campo-${index}`} className="formularios__campo-row">
                    <label>
                      <span>Chave</span>
                      <input
                        value={campo.chave}
                        onChange={(event) => handleUpdateCampo(index, { chave: event.target.value })}
                      />
                    </label>
                    <label>
                      <span>Tipo</span>
                      <select
                        value={campo.tipo}
                        onChange={(event) => handleUpdateCampo(index, { tipo: event.target.value })}
                      >
                        {FIELD_TYPES.map((tipo) => (
                          <option key={tipo.value} value={tipo.value}>
                            {tipo.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Ordem</span>
                      <input
                        type="number"
                        value={campo.ordem}
                        onChange={(event) => handleUpdateCampo(index, { ordem: Number(event.target.value) })}
                      />
                    </label>
                    <label>
                      <span>Obrigatório</span>
                      <select
                        value={campo.obrigatorio ? 'true' : 'false'}
                        onChange={(event) => handleUpdateCampo(index, { obrigatorio: event.target.value === 'true' })}
                      >
                        <option value="false">Não</option>
                        <option value="true">Sim</option>
                      </select>
                    </label>
                    <label className="full">
                      <span>Config JSON</span>
                      <textarea
                        rows={2}
                        value={campo.configJson}
                        onChange={(event) => handleUpdateCampo(index, { configJson: event.target.value })}
                        placeholder='{"options":["A","B"]}'
                      />
                    </label>
                    <button type="button" className="ghost" onClick={() => handleRemoveCampo(index)}>
                      Remover
                    </button>
                  </div>
                ))
              )}
            </div>

            {createFeedback && <p className="formularios__feedback">{createFeedback}</p>}

            <div className="formularios__actions">
              <button type="submit" disabled={createFormulario.isPending || createCampo.isPending}>
                {createFormulario.isPending ? 'Criando...' : 'Criar formulário'}
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}
