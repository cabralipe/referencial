import { FormEvent, useState } from 'react';
import { useParams } from 'react-router-dom';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useFormularioInscricaoPublic, useEnviarInscricao } from '@/hooks/useFormulariosInscricao';

import './InscricaoPublicaPage.css';

export function InscricaoPublicaPage() {
  const { token } = useParams<{ token: string }>();
  const { data: formulario, isLoading, error } = useFormularioInscricaoPublic(token);
  const enviarInscricao = useEnviarInscricao();

  const [nomeCompleto, setNomeCompleto] = useState('');
  const [instituicao, setInstituicao] = useState('');
  const [telefone, setTelefone] = useState('');
  const [email, setEmail] = useState('');
  const [areasAtuacao, setAreasAtuacao] = useState<string[]>([]);
  const [areaOutro, setAreaOutro] = useState('');
  const [representacoes, setRepresentacoes] = useState<string[]>([]);
  const [repOutro, setRepOutro] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const toggleArea = (opcao: string) => {
    setAreasAtuacao((prev) =>
      prev.includes(opcao) ? prev.filter((v) => v !== opcao) : [...prev, opcao],
    );
  };

  const toggleRep = (opcao: string) => {
    setRepresentacoes((prev) =>
      prev.includes(opcao) ? prev.filter((v) => v !== opcao) : [...prev, opcao],
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !formulario) return;
    setErro(null);
    setFeedback(null);

    const areasFinais = areaOutro.trim()
      ? [...areasAtuacao, `Outro: ${areaOutro.trim()}`]
      : areasAtuacao;
    const repsFinais = repOutro.trim()
      ? [...representacoes, `Outro: ${repOutro.trim()}`]
      : representacoes;

    try {
      await enviarInscricao.mutateAsync({
        token,
        nome_completo: nomeCompleto.trim(),
        instituicao_comunidade: instituicao.trim(),
        telefone: telefone.trim(),
        email: email.trim(),
        areas_atuacao: areasFinais,
        area_atuacao_outro: areaOutro.trim(),
        representacoes: repsFinais,
        representacao_outro: repOutro.trim(),
      });
      setFeedback('Inscrição realizada com sucesso! Obrigado pela participação.');
      setNomeCompleto('');
      setInstituicao('');
      setTelefone('');
      setEmail('');
      setAreasAtuacao([]);
      setAreaOutro('');
      setRepresentacoes([]);
      setRepOutro('');
    } catch (err: any) {
      setErro(err?.message ?? 'Não foi possível enviar a inscrição.');
    }
  };

  if (isLoading && !formulario) {
    return <FullPageLoader message="Carregando formulário..." />;
  }

  if (error || !formulario) {
    return (
      <div className="inscricao-publica">
        <div className="inscricao-publica__card">
          <h1>Formulário de Inscrição</h1>
          <p>Este formulário não foi encontrado ou não está mais disponível.</p>
        </div>
      </div>
    );
  }

  if (!formulario.ativo) {
    return (
      <div className="inscricao-publica">
        <div className="inscricao-publica__card">
          <h1>{formulario.titulo}</h1>
          <p className="inscricao-publica__encerrado">Este formulário está encerrado e não aceita novas inscrições.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="inscricao-publica">
      <header className="inscricao-publica__hero">
        <span className="inscricao-publica__chip">Formulário de Inscrição</span>
        <h1>{formulario.titulo}</h1>
        {formulario.subtitulo && <h2>{formulario.subtitulo}</h2>}
        {formulario.descricao && <p>{formulario.descricao}</p>}
      </header>

      <div className="inscricao-publica__card">
        {feedback && <div className="inscricao-publica__alert success">{feedback}</div>}
        {erro && <div className="inscricao-publica__alert danger">{erro}</div>}

        {!feedback && (
          <form className="inscricao-publica__form" onSubmit={handleSubmit}>
            <section className="inscricao-publica__section">
              <h3>Dados do Participante</h3>
              <div className="inscricao-publica__grid">
                <label className="full">
                  <span>Nome Completo <span className="required">*</span></span>
                  <input
                    type="text"
                    required
                    value={nomeCompleto}
                    onChange={(e) => setNomeCompleto(e.target.value)}
                    placeholder="Seu nome completo"
                  />
                </label>
                <label>
                  <span>Instituição / Comunidade</span>
                  <input
                    type="text"
                    value={instituicao}
                    onChange={(e) => setInstituicao(e.target.value)}
                    placeholder="Nome da instituição ou comunidade"
                  />
                </label>
                <label>
                  <span>Telefone</span>
                  <input
                    type="tel"
                    value={telefone}
                    onChange={(e) => setTelefone(e.target.value)}
                    placeholder="(00) 00000-0000"
                  />
                </label>
                <label>
                  <span>E-mail</span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="seu@email.com"
                  />
                </label>
              </div>
            </section>

            {formulario.opcoes_area_atuacao && formulario.opcoes_area_atuacao.length > 0 && (
              <section className="inscricao-publica__section">
                <h3>Área de Atuação</h3>
                <p className="inscricao-publica__hint">Selecione a(s) área(s) que melhor descrevem sua atuação.</p>
                <div className="inscricao-publica__checkboxes">
                  {formulario.opcoes_area_atuacao.map((opcao) => (
                    <label key={opcao} className={`inscricao-publica__check ${areasAtuacao.includes(opcao) ? 'is-checked' : ''}`}>
                      <input
                        type="checkbox"
                        checked={areasAtuacao.includes(opcao)}
                        onChange={() => toggleArea(opcao)}
                      />
                      <span>{opcao}</span>
                    </label>
                  ))}
                  <div className="inscricao-publica__outro">
                    <label className={`inscricao-publica__check ${areaOutro ? 'is-checked' : ''}`}>
                      <input
                        type="checkbox"
                        checked={Boolean(areaOutro)}
                        onChange={(e) => { if (!e.target.checked) setAreaOutro(''); }}
                        readOnly
                      />
                      <span>Outro:</span>
                    </label>
                    <input
                      type="text"
                      value={areaOutro}
                      onChange={(e) => setAreaOutro(e.target.value)}
                      placeholder="Especifique sua área"
                      className="inscricao-publica__outro-input"
                    />
                  </div>
                </div>
              </section>
            )}

            {formulario.opcoes_representacao && formulario.opcoes_representacao.length > 0 && (
              <section className="inscricao-publica__section">
                <h3>Representação</h3>
                <p className="inscricao-publica__hint">Assinale a representação da qual faz parte.</p>
                <div className="inscricao-publica__checkboxes">
                  {formulario.opcoes_representacao.map((opcao) => (
                    <label key={opcao} className={`inscricao-publica__check ${representacoes.includes(opcao) ? 'is-checked' : ''}`}>
                      <input
                        type="checkbox"
                        checked={representacoes.includes(opcao)}
                        onChange={() => toggleRep(opcao)}
                      />
                      <span>{opcao}</span>
                    </label>
                  ))}
                  <div className="inscricao-publica__outro">
                    <label className={`inscricao-publica__check ${repOutro ? 'is-checked' : ''}`}>
                      <input
                        type="checkbox"
                        checked={Boolean(repOutro)}
                        onChange={(e) => { if (!e.target.checked) setRepOutro(''); }}
                        readOnly
                      />
                      <span>Outro:</span>
                    </label>
                    <input
                      type="text"
                      value={repOutro}
                      onChange={(e) => setRepOutro(e.target.value)}
                      placeholder="Especifique sua representação"
                      className="inscricao-publica__outro-input"
                    />
                  </div>
                </div>
              </section>
            )}

            <div className="inscricao-publica__submit">
              <button type="submit" disabled={enviarInscricao.isPending}>
                {enviarInscricao.isPending ? 'Enviando...' : 'Confirmar Inscrição'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
