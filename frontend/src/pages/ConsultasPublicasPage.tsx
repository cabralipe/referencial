import { FormEvent, useMemo, useState } from 'react';

import { ApiError } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import {
  useConsultasPublicas,
  useCriarConsultaPublica,
  useExcluirConsultaPublica,
  useManifestacoesConsulta,
} from '@/hooks/useConsultasPublicas';
import type { ConsultaPublica } from '@/api/types';

import './ConsultasPublicasPage.css';

interface PerguntaFormItem {
  pergunta: string;
  opcoesTexto: string; // raw textarea value (one option per line)
}

export function ConsultasPublicasPage() {
  const {
    data: consultas,
    isLoading,
    error: consultasError,
    refetch: refetchConsultas,
  } = useConsultasPublicas();
  const criarConsulta = useCriarConsultaPublica();
  const excluirConsulta = useExcluirConsultaPublica();
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [consultaSelecionada, setConsultaSelecionada] = useState<number | null>(null);
  const [perguntas, setPerguntas] = useState<PerguntaFormItem[]>([]);
  const { data: manifestacoes, isLoading: carregandoManifestacoes } = useManifestacoesConsulta(consultaSelecionada ?? undefined);

  const consultaFetchErro = useMemo(() => {
    if (!consultasError) return null;
    if (consultasError instanceof ApiError) return consultasError.message;
    if (consultasError instanceof Error) return consultasError.message;
    return 'Não foi possível carregar as consultas públicas.';
  }, [consultasError]);

  const addPergunta = () => {
    setPerguntas((prev) => [...prev, { pergunta: '', opcoesTexto: '' }]);
  };

  const removePergunta = (index: number) => {
    setPerguntas((prev) => prev.filter((_, i) => i !== index));
  };

  const updatePergunta = (index: number, field: keyof PerguntaFormItem, value: string) => {
    setPerguntas((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)),
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    setMensagem(null);
    setErro(null);
    if (pdfFile && !pdfFile.type.toLowerCase().includes('pdf') && !pdfFile.name.toLowerCase().endsWith('.pdf')) {
      setErro('Envie um arquivo PDF válido (extensão .pdf).');
      return;
    }
    if (pdfFile && pdfFile.size === 0) {
      setErro('O PDF parece estar vazio. Tente reenviar o arquivo.');
      return;
    }
    const form = new FormData(formElement);
    const titulo = String(form.get('titulo') ?? '').trim();
    const slug = String(form.get('slug') ?? '').trim();
    const descricao = String(form.get('descricao') ?? '').trim();
    const data_publicacao = String(form.get('data_publicacao') ?? '').trim();
    const data_validade = String(form.get('data_validade') ?? '').trim() || undefined;
    const data_fechamento = String(form.get('data_fechamento') ?? '').trim() || undefined;
    const ativa = form.get('ativa') !== null;

    if (!titulo || !data_publicacao || !pdfFile) {
      setErro('Preencha título, data de publicação e selecione o PDF.');
      return;
    }

    // Build perguntas_votacao from state
    const perguntas_votacao = perguntas
      .filter((p) => p.pergunta.trim())
      .map((p) => ({
        pergunta: p.pergunta.trim(),
        opcoes: p.opcoesTexto
          .split('\n')
          .map((l) => l.trim())
          .filter(Boolean),
      }));

    try {
      await criarConsulta.mutateAsync({
        titulo,
        slug: slug || undefined,
        descricao: descricao || undefined,
        pdf: pdfFile,
        data_publicacao,
        data_validade,
        data_fechamento,
        perguntas_votacao: perguntas_votacao.length > 0 ? perguntas_votacao : undefined,
        ativa,
      });
      setMensagem('Consulta criada com sucesso! Compartilhe o link público para iniciar a participação.');
      setPerguntas([]);
      setPdfFile(null);
      formElement.reset();
    } catch (error: any) {
      setErro(error?.message ?? 'Não foi possível criar a consulta.');
    }
  };

  const handleCopyLink = async (consulta: ConsultaPublica) => {
    const texto = consulta.public_url || `${window.location.origin}/consultas-publicas/${consulta.token_acesso}`;
    try {
      await navigator.clipboard.writeText(texto);
      setMensagem('Link copiado para a área de transferência.');
    } catch (error) {
      setErro('Não foi possível copiar o link automaticamente.');
    }
  };

  const handleDelete = async (consulta: ConsultaPublica) => {
    const confirmado = window.confirm(`Excluir a consulta pública "${consulta.titulo}"? Esta ação não pode ser desfeita.`);
    if (!confirmado) return;
    setErro(null);
    setMensagem(null);
    try {
      await excluirConsulta.mutateAsync(consulta.id);
      setMensagem('Consulta removida.');
    } catch (error: any) {
      setErro(error?.message ?? 'Não foi possível excluir a consulta.');
    }
  };

  if (isLoading && !consultas) {
    return <FullPageLoader message="Carregando consultas públicas..." />;
  }

  return (
    <div className="consultas-admin">
      <header className="consultas-admin__header">
        <div>
          <h1>Consultas públicas</h1>
          <p>Publique documentos finais em PDF, receba comentários por página e registre votos com identificação.</p>
        </div>
      </header>

      <PageInstructions
        title="Fluxo sugerido"
        description="Mantenha o processo simples para o público, mas completo para auditoria."
        items={[
          { title: 'Cadastre o PDF', description: 'Suba o documento final do GT com título e datas de abertura/encerramento.' },
          { title: 'Defina a votação', description: 'Crie perguntas objetivas com opções claras; o nome/CPF são coletados ao enviar.' },
          { title: 'Compartilhe o link', description: 'Use o link público gerado para divulgar a consulta aberta.' },
        ]}
      />

      <section className="consultas-admin__form-card">
        <div className="consultas-admin__form-header">
          <div>
            <h2>Nova consulta pública</h2>
            <p>Envie um PDF, defina datas e adicione perguntas de votação (opcional).</p>
          </div>
          {mensagem && <span className="consultas-admin__badge success">{mensagem}</span>}
          {erro && <span className="consultas-admin__badge danger">{erro}</span>}
        </div>
        <form className="consultas-admin__form" onSubmit={handleSubmit}>
          <label>
            <span>Título</span>
            <input name="titulo" type="text" placeholder="Ex.: Documento final do GT Alfabetização" required />
          </label>
          <label>
            <span>Slug (opcional)</span>
            <input name="slug" type="text" placeholder="documento-gt-alfabetizacao" />
          </label>
          <label className="full">
            <span>Descrição curta (opcional)</span>
            <textarea name="descricao" rows={3} placeholder="Contextualize o documento e a consulta pública" />
          </label>
          <label>
            <span>PDF</span>
            <input
              name="pdf"
              type="file"
              accept="application/pdf"
              required
              onChange={(event) => setPdfFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <label>
            <span>Data de publicação</span>
            <input name="data_publicacao" type="date" required defaultValue={new Date().toISOString().slice(0, 10)} />
          </label>
          <label>
            <span>Validade da consulta (opcional)</span>
            <input name="data_validade" type="date" />
          </label>
          <label>
            <span>Fechamento (opcional)</span>
            <input name="data_fechamento" type="date" />
          </label>

          {/* ── Multiple questions section ── */}
          <div className="full consultas-admin__perguntas-section">
            <div className="consultas-admin__perguntas-header">
              <span>Perguntas de votação (opcional)</span>
              <button type="button" className="consultas-admin__add-pergunta" onClick={addPergunta}>
                + Adicionar pergunta
              </button>
            </div>
            {perguntas.map((p, index) => (
              <div key={index} className="consultas-admin__pergunta-item">
                <div className="consultas-admin__pergunta-top">
                  <span className="consultas-admin__pergunta-number">{index + 1}</span>
                  <input
                    type="text"
                    placeholder="Ex.: Você concorda com o documento?"
                    value={p.pergunta}
                    onChange={(e) => updatePergunta(index, 'pergunta', e.target.value)}
                  />
                  <button
                    type="button"
                    className="consultas-admin__remove-pergunta"
                    onClick={() => removePergunta(index)}
                    title="Remover pergunta"
                  >
                    ✕
                  </button>
                </div>
                <textarea
                  rows={2}
                  placeholder={"Opções de voto (uma por linha)\nEx.: Sim\nNão"}
                  value={p.opcoesTexto}
                  onChange={(e) => updatePergunta(index, 'opcoesTexto', e.target.value)}
                />
              </div>
            ))}
            {perguntas.length === 0 && (
              <p className="consultas-admin__perguntas-empty">
                Nenhuma pergunta adicionada. Clique em "+ Adicionar pergunta" para criar uma.
              </p>
            )}
          </div>

          <label className="checkbox">
            <input name="ativa" type="checkbox" defaultChecked />
            <span>Consulta ativa</span>
          </label>
          <button type="submit" disabled={criarConsulta.isPending}>
            {criarConsulta.isPending ? 'Publicando...' : 'Publicar consulta'}
          </button>
        </form>
      </section>

      <section>
        <div className="consultas-admin__section-header">
          <h2>Consultas publicadas</h2>
          <p>Compartilhe o link aberto e acompanhe manifestações por página do PDF.</p>
        </div>
        {consultaFetchErro && (
          <div className="consultas-admin__alert">
            <strong>Erro ao carregar consultas.</strong>
            <p>{consultaFetchErro}</p>
            <button type="button" className="ghost" onClick={() => refetchConsultas()}>
              Tentar novamente
            </button>
          </div>
        )}
        {consultas && consultas.length > 0 ? (
          <div className="consultas-admin__grid">
            {consultas.map((consulta) => (
              <article key={consulta.id} className="consultas-admin__card">
                <header>
                  <div>
                    <h3>{consulta.titulo}</h3>
                    <p>{consulta.descricao || 'Sem descrição.'}</p>
                  </div>
                  <span className={`status-pill ${consulta.ativa ? 'on' : 'off'}`}>
                    {consulta.ativa ? 'Ativa' : 'Inativa'}
                  </span>
                </header>
                <dl className="consultas-admin__meta">
                  <div>
                    <dt>Publicação</dt>
                    <dd>{new Date(consulta.data_publicacao).toLocaleDateString('pt-BR')}</dd>
                  </div>
                  <div>
                    <dt>Validade</dt>
                    <dd>{consulta.data_validade ? new Date(consulta.data_validade).toLocaleDateString('pt-BR') : '—'}</dd>
                  </div>
                  <div>
                    <dt>Encerramento</dt>
                    <dd>{consulta.data_fechamento ? new Date(consulta.data_fechamento).toLocaleDateString('pt-BR') : '—'}</dd>
                  </div>
                  <div>
                    <dt>Manifestações</dt>
                    <dd>{consulta.total_manifestacoes}</dd>
                  </div>
                </dl>
                <div className="consultas-admin__public-link">
                  <div>
                    <small>Link público</small>
                    <a href={consulta.public_url} target="_blank" rel="noreferrer">
                      {consulta.public_url}
                    </a>
                  </div>
                  <button type="button" className="ghost" onClick={() => handleCopyLink(consulta)}>
                    Copiar
                  </button>
                </div>
                {consulta.perguntas_votacao && consulta.perguntas_votacao.length > 0 && (
                  <div className="consultas-admin__poll">
                    {consulta.perguntas_votacao.map((pv, idx) => (
                      <div key={idx} className="consultas-admin__poll-item">
                        <strong>{pv.pergunta}</strong>
                        {pv.opcoes.length > 0 && (
                          <ul>
                            {pv.opcoes.map((opcao) => (
                              <li key={opcao}>{opcao}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <div className="consultas-admin__actions">
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => setConsultaSelecionada((prev) => (prev === consulta.id ? null : consulta.id))}
                  >
                    {consultaSelecionada === consulta.id ? 'Fechar manifestações' : 'Ver manifestações'}
                  </button>
                  <button
                    type="button"
                    className="danger"
                    disabled={excluirConsulta.isPending}
                    onClick={() => handleDelete(consulta)}
                  >
                    {excluirConsulta.isPending ? 'Excluindo...' : 'Excluir'}
                  </button>
                </div>
                {consultaSelecionada === consulta.id && (
                  <div className="consultas-admin__manifestacoes">
                    {carregandoManifestacoes && <p>Carregando manifestações...</p>}
                    {!carregandoManifestacoes && manifestacoes && manifestacoes.length === 0 && (
                      <p className="muted">Nenhuma manifestação registrada ainda.</p>
                    )}
                    {!carregandoManifestacoes &&
                      manifestacoes &&
                      manifestacoes.map((item) => (
                        <div key={item.id} className="manifestacao">
                          <div className="manifestacao__header">
                            <span>#{item.id}</span>
                            <span>{item.pagina ? `Página ${item.pagina}` : 'Comentário geral'}</span>
                            <span>{new Date(item.created_at).toLocaleString('pt-BR')}</span>
                          </div>
                          <p>{item.comentario}</p>
                          {item.votos && item.votos.length > 0 && item.votos.some((v) => v) && (
                            <div className="manifestacao__votos">
                              {item.votos.map((v, vi) => (
                                v ? (
                                  <span key={vi} className="manifestacao__voto">
                                    {consulta.perguntas_votacao?.[vi]?.pergunta
                                      ? `${consulta.perguntas_votacao[vi].pergunta}: ${v}`
                                      : `Voto ${vi + 1}: ${v}`}
                                  </span>
                                ) : null
                              ))}
                            </div>
                          )}
                          <small>
                            {item.nome_completo} — {item.cidade}/{item.estado}
                          </small>
                        </div>
                      ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="consultas-admin__empty">
            <p>Nenhuma consulta publicada ainda.</p>
          </div>
        )}
      </section>
    </div>
  );
}
