import { FormEvent, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import {
  useConsultaPublicaPublic,
  useEnviarManifestacao,
  useManifestacoesPublicas,
} from '@/hooks/useConsultasPublicas';

import './ConsultaPublicaPublicPage.css';

function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('pt-BR');
}

export function ConsultaPublicaPublicPage() {
  const { token } = useParams<{ token: string }>();
  const { data: consulta, isLoading, error } = useConsultaPublicaPublic(token);
  const { data: manifestacoes, refetch } = useManifestacoesPublicas(token);
  const enviarManifestacao = useEnviarManifestacao();

  const [pagina, setPagina] = useState('');
  const [comentario, setComentario] = useState('');
  const [voto, setVoto] = useState('');
  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [cidade, setCidade] = useState('');
  const [estado, setEstado] = useState('');
  const [email, setEmail] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const podeParticipar = useMemo(() => consulta?.esta_disponivel !== false, [consulta?.esta_disponivel]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !consulta) return;
    setErro(null);
    setFeedback(null);

    const payload = {
      token,
      pagina: pagina ? Number(pagina) : null,
      comentario: comentario.trim(),
      voto: voto.trim(),
      nome_completo: nome.trim(),
      cpf: cpf.trim(),
      cidade: cidade.trim(),
      estado: estado.trim().toUpperCase(),
      contato_email: email.trim() || undefined,
    };

    if (!payload.comentario && !payload.voto) {
      setErro('Escreva um comentário ou escolha uma opção de voto.');
      return;
    }

    try {
      await enviarManifestacao.mutateAsync(payload);
      setFeedback('Contribuição registrada! Obrigado por participar.');
      setComentario('');
      setVoto('');
      setPagina('');
      setNome('');
      setCpf('');
      setCidade('');
      setEstado('');
      setEmail('');
      refetch();
    } catch (submitError: any) {
      setErro(submitError?.message ?? 'Não foi possível enviar a manifestação.');
    }
  };

  if (isLoading && !consulta) {
    return <FullPageLoader message="Carregando consulta pública..." />;
  }

  if (error) {
    return (
      <div className="consulta-publica">
        <div className="consulta-publica__card">
          <h1>Consulta pública</h1>
          <p>Não encontramos esta consulta ou o período já foi encerrado.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="consulta-publica">
      <header className="consulta-publica__hero">
        <div>
          <span className="consulta-publica__chip">Consulta pública</span>
          <h1>{consulta?.titulo ?? 'Consulta'}</h1>
          <p>{consulta?.descricao || 'Documento disponível para leitura, comentários por página e voto com identificação.'}</p>
          <div className="consulta-publica__meta">
            <span>Publicação: {formatDate(consulta?.data_publicacao)}</span>
            <span>Validade: {formatDate(consulta?.data_validade)}</span>
            <span>Encerramento: {formatDate(consulta?.data_fechamento)}</span>
          </div>
        </div>
      </header>

      <div className="consulta-publica__content">
        <section className="consulta-publica__panel pdf">
          <div className="consulta-publica__panel-header">
            <div>
              <h2>Documento em PDF</h2>
              <p>Use o visualizador para navegar por páginas antes de comentar.</p>
            </div>
          </div>
          {consulta?.pdf_url ? (
            <iframe src={consulta.pdf_url} title="PDF da consulta" className="consulta-publica__pdf" />
          ) : (
            <div className="consulta-publica__empty">PDF não encontrado.</div>
          )}
        </section>

        <section className="consulta-publica__panel">
          <div className="consulta-publica__panel-header">
            <div>
              <h2>Manifestar opinião</h2>
              <p>Deixe um comentário geral ou indique a página específica. Vote se desejar.</p>
            </div>
            {!podeParticipar && <span className="consulta-publica__chip warning">Encerrada</span>}
          </div>

          {feedback && <div className="consulta-publica__alert success">{feedback}</div>}
          {erro && <div className="consulta-publica__alert danger">{erro}</div>}

          <form className="consulta-publica__form" onSubmit={handleSubmit}>
            <label>
              <span>Página do PDF (opcional)</span>
              <input
                type="number"
                min={1}
                value={pagina}
                onChange={(event) => setPagina(event.target.value)}
                placeholder="Ex.: 3"
              />
            </label>
            <label className="full">
              <span>Comentário</span>
              <textarea
                rows={4}
                value={comentario}
                onChange={(event) => setComentario(event.target.value)}
                placeholder="Descreva sua sugestão ou apontamento sobre esta página ou o documento geral"
              />
            </label>

            {consulta?.pergunta_votacao && (
              <div className="consulta-publica__poll full">
                <strong>{consulta.pergunta_votacao}</strong>
                <div className="consulta-publica__options">
                  {(consulta.opcoes_votacao || []).map((opcao) => (
                    <label key={opcao} className={voto === opcao ? 'is-selected' : ''}>
                      <input
                        type="radio"
                        name="voto"
                        value={opcao}
                        checked={voto === opcao}
                        onChange={() => setVoto(opcao)}
                      />
                      <span>{opcao}</span>
                    </label>
                  ))}
                  <label className={!voto ? 'is-selected' : ''}>
                    <input type="radio" name="voto" value="" checked={!voto} onChange={() => setVoto('')} />
                    <span>Sem voto</span>
                  </label>
                </div>
              </div>
            )}

            <div className="consulta-publica__identificacao full">
              <h3>Identificação para registrar a consulta</h3>
              <p>Esses dados são necessários para validar a contribuição.</p>
              <div className="consulta-publica__identificacao-grid">
                <label>
                  <span>Nome completo</span>
                  <input type="text" required value={nome} onChange={(event) => setNome(event.target.value)} />
                </label>
                <label>
                  <span>CPF</span>
                  <input type="text" required value={cpf} onChange={(event) => setCpf(event.target.value)} />
                </label>
                <label>
                  <span>Cidade</span>
                  <input type="text" required value={cidade} onChange={(event) => setCidade(event.target.value)} />
                </label>
                <label>
                  <span>Estado (UF)</span>
                  <input
                    type="text"
                    required
                    maxLength={2}
                    value={estado}
                    onChange={(event) => setEstado(event.target.value.toUpperCase())}
                  />
                </label>
                <label>
                  <span>E-mail (opcional)</span>
                  <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
                </label>
              </div>
            </div>

            <button type="submit" disabled={enviarManifestacao.isPending || !podeParticipar}>
              {enviarManifestacao.isPending ? 'Enviando...' : 'Registrar manifestação'}
            </button>
          </form>
        </section>

        <section className="consulta-publica__panel">
          <div className="consulta-publica__panel-header">
            <div>
              <h2>Comentários e votos registrados</h2>
              <p>Transparência das contribuições públicas (dados sensíveis são omitidos).</p>
            </div>
            <span className="consulta-publica__chip neutral">
              {consulta?.total_manifestacoes ?? 0} manifestação{(consulta?.total_manifestacoes ?? 0) === 1 ? '' : 's'}
            </span>
          </div>
          <div className="consulta-publica__manifestacoes">
            {manifestacoes && manifestacoes.length > 0 ? (
              manifestacoes.map((item) => (
                <div key={item.id} className="manifestacao-publica">
                  <div className="manifestacao-publica__header">
                    <span>{item.pagina ? `Página ${item.pagina}` : 'Comentário geral'}</span>
                    <span>{new Date(item.created_at).toLocaleString('pt-BR')}</span>
                  </div>
                  <p>{item.comentario}</p>
                  {(item.voto || '').trim() && <span className="manifestacao-publica__voto">Voto: {item.voto}</span>}
                  <small>
                    {item.nome_completo} — {item.cidade}/{item.estado}
                  </small>
                </div>
              ))
            ) : (
              <div className="consulta-publica__empty">Nenhuma manifestação registrada ainda.</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
