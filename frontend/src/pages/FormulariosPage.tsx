import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCamposFormulario, useFormularios, useSubmitFormulario } from '@/hooks/useFormularios';

import './FormulariosPage.css';

type ValorCampo = string | number | boolean | null;

export function FormulariosPage() {
  const { data: formularios, isLoading } = useFormularios();
  const [selectedFormulario, setSelectedFormulario] = useState<number | null>(null);
  const [ownerType, setOwnerType] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [values, setValues] = useState<Record<number, ValorCampo>>({});
  const [feedback, setFeedback] = useState<string | null>(null);

  const { data: campos, isFetching: camposLoading } = useCamposFormulario(selectedFormulario ?? undefined);
  const submitFormulario = useSubmitFormulario();

  const formularioSelecionado = useMemo(
    () => formularios?.find((item) => item.id === selectedFormulario) ?? null,
    [formularios, selectedFormulario],
  );

  const handleChange = (campoId: number, valor: ValorCampo) => {
    setValues((prev) => ({
      ...prev,
      [campoId]: valor,
    }));
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
                  <span>Owner type</span>
                  <input
                    type="text"
                    value={ownerType}
                    onChange={(event) => setOwnerType(event.target.value)}
                    placeholder="Ex.: tarefa"
                  />
                </label>
                <label>
                  <span>Owner ID</span>
                  <input
                    type="number"
                    value={ownerId}
                    onChange={(event) => setOwnerId(event.target.value)}
                    placeholder="Ex.: 12"
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
    </div>
  );
}
