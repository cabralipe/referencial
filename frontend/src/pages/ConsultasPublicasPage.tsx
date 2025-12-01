import { FormEvent, useMemo, useState } from 'react';

import { ApiError } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useConsultasPublicas, useCriarConsultaPublica, useManifestacoesConsulta } from '@/hooks/useConsultasPublicas';
import type { ConsultaPublica } from '@/api/types';

import './ConsultasPublicasPage.css';

export function ConsultasPublicasPage() {
  const {
    data: consultas,
    isLoading,
    error: consultasError,
    refetch: refetchConsultas,
  } = useConsultasPublicas();
  const criarConsulta = useCriarConsultaPublica();
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [opcoesTexto, setOpcoesTexto] = useState('');
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [consultaSelecionada, setConsultaSelecionada] = useState<number | null>(null);
  const { data: manifestacoes, isLoading: carregandoManifestacoes } = useManifestacoesConsulta(consultaSelecionada ?? undefined);

  const consultaFetchErro = useMemo(() => {
    if (!consultasError) return null;
    if (consultasError instanceof ApiError) return consultasError.message;
    if (consultasError instanceof Error) return consultasError.message;
    return 'Não foi possível carregar as consultas públicas.';
  }, [consultasError]);

  const opcoesVotacao = useMemo(
    () =>
      opcoesTexto
        .split('\n')
        .map((linha) => linha.trim())
        .filter(Boolean),
    [opcoesTexto],
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMensagem(null);
    setErro(null);
    const form = new FormData(event.currentTarget);
    const titulo = String(form.get('titulo') ?? '').trim();
    const slug = String(form.get('slug') ?? '').trim();
    const descricao = String(form.get('descricao') ?? '').trim();
    const data_publicacao = String(form.get('data_publicacao') ?? '').trim();
    const data_validade = String(form.get('data_validade') ?? '').trim() || undefined;
    const data_fechamento = String(form.get('data_fechamento') ?? '').trim() || undefined;
    const pergunta_votacao = String(form.get('pergunta_votacao') ?? '').trim() || undefined;
    const ativa = form.get('ativa') !== null;

    if (!titulo || !data_publicacao || !pdfFile) {
      setErro('Preencha título, data de publicação e selecione o PDF.');
      return;
    }

    try {
      await criarConsulta.mutateAsync({
        titulo,
        slug: slug || undefined,
        descricao: descricao || undefined,
        pdf: pdfFile,
        data_publicacao,
        data_validade,
        data_fechamento,
        pergunta_votacao,
        opcoes_votacao: opcoesVotacao,
        ativa,
      });
      setMensagem('Consulta criada com sucesso! Compartilhe o link público para iniciar a participação.');
      setOpcoesTexto('');
      setPdfFile(null);
      event.currentTarget.reset();
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
          { title: 'Defina a votação', description: 'Crie uma pergunta objetiva e opções claras; o nome/CPF são coletados ao enviar.' },
          { title: 'Compartilhe o link', description: 'Use o link público gerado para divulgar a consulta aberta.' },
        ]}
      />

      <section className="consultas-admin__form-card">
        <div className="consultas-admin__form-header">
          <div>
            <h2>Nova consulta pública</h2>
            <p>Envie um PDF, defina datas e personalize a pergunta de votação (opcional).</p>
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
          <label>
            <span>Pergunta de votação (opcional)</span>
            <input name="pergunta_votacao" type="text" placeholder="Você concorda com o documento?" />
          </label>
          <label className="full">
            <span>Opções de voto (uma por linha)</span>
            <textarea
              rows={3}
              value={opcoesTexto}
              onChange={(event) => setOpcoesTexto(event.target.value)}
              placeholder="Sim&#10;Não"
            />
          </label>
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
                {consulta.pergunta_votacao && (
                  <div className="consultas-admin__poll">
                    <strong>{consulta.pergunta_votacao}</strong>
                    <ul>
                      {(consulta.opcoes_votacao || []).map((opcao) => (
                        <li key={opcao}>{opcao}</li>
                      ))}
                    </ul>
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
                          {(item.voto || '').trim() && <span className="manifestacao__voto">Voto: {item.voto}</span>}
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
