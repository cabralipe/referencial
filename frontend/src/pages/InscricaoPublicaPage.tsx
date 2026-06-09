import { FormEvent, useState } from 'react';
import { useParams } from 'react-router-dom';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useFormularioInscricaoPublic, useEnviarInscricao } from '@/hooks/useFormulariosInscricao';
import type { CampoFormulario } from '@/api/types';

import './InscricaoPublicaPage.css';

const CAMPOS_PADRAO: CampoFormulario[] = [
  { chave: 'nome_completo', label: 'Nome Completo', tipo: 'text', obrigatorio: true, ordem: 1, ativo: true, padrao: true },
  { chave: 'instituicao_comunidade', label: 'Instituição / Comunidade', tipo: 'text', obrigatorio: false, ordem: 2, ativo: true, padrao: true },
  { chave: 'telefone', label: 'Telefone', tipo: 'tel', obrigatorio: false, ordem: 3, ativo: true, padrao: true },
  { chave: 'email', label: 'E-mail', tipo: 'email', obrigatorio: false, ordem: 4, ativo: true, padrao: true },
  { chave: 'areas_atuacao', label: 'Área de Atuação', tipo: 'checkbox_group', obrigatorio: false, ordem: 5, ativo: true, padrao: true },
  { chave: 'representacoes', label: 'Representação', tipo: 'checkbox_group', obrigatorio: false, ordem: 6, ativo: true, padrao: true },
];

export function InscricaoPublicaPage() {
  const { token } = useParams<{ token: string }>();
  const { data: formulario, isLoading, error } = useFormularioInscricaoPublic(token);
  const enviarInscricao = useEnviarInscricao();

  // Valores dos campos padrão
  const [nomeCompleto, setNomeCompleto] = useState('');
  const [instituicao, setInstituicao] = useState('');
  const [telefone, setTelefone] = useState('');
  const [email, setEmail] = useState('');
  const [areasAtuacao, setAreasAtuacao] = useState<string[]>([]);
  const [areaOutro, setAreaOutro] = useState('');
  const [representacoes, setRepresentacoes] = useState<string[]>([]);
  const [repOutro, setRepOutro] = useState('');

  // Valores dos campos extras (customizados)
  const [valoresExtras, setValoresExtras] = useState<Record<string, string | string[]>>({});
  const [arquivosExtras, setArquivosExtras] = useState<Record<string, File | null>>({});

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

  const toggleExtraCheckbox = (chave: string, opcao: string) => {
    setValoresExtras((prev) => {
      const atual = (prev[chave] as string[] | undefined) ?? [];
      const novo = atual.includes(opcao)
        ? atual.filter((v) => v !== opcao)
        : [...atual, opcao];
      return { ...prev, [chave]: novo };
    });
  };

  const setExtraValor = (chave: string, valor: string) => {
    setValoresExtras((prev) => ({ ...prev, [chave]: valor }));
  };

  const setExtraArquivo = (chave: string, arquivo: File | null) => {
    setArquivosExtras((prev) => ({ ...prev, [chave]: arquivo }));
  };

  const camposEfetivos: CampoFormulario[] = formulario?.campos_efetivos?.length
    ? formulario.campos_efetivos
    : CAMPOS_PADRAO;

  const camposAtivos = camposEfetivos
    .filter((c) => c.ativo)
    .sort((a, b) => a.ordem - b.ordem);

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

    // Dados extras (campos customizados)
    const dados_extras: Record<string, unknown> = {};
    for (const [chave, valor] of Object.entries(valoresExtras)) {
      dados_extras[chave] = valor;
    }

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
        dados_extras: Object.keys(dados_extras).length > 0 ? dados_extras : undefined,
        arquivos: arquivosExtras,
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
      setValoresExtras({});
      setArquivosExtras({});
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

  const renderCampoPadrao = (campo: CampoFormulario) => {
    if (campo.chave === 'nome_completo') {
      return (
        <label key="nome_completo" className="full">
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <input
            type="text"
            required={campo.obrigatorio}
            value={nomeCompleto}
            onChange={(e) => setNomeCompleto(e.target.value)}
            placeholder="Seu nome completo"
          />
        </label>
      );
    }
    if (campo.chave === 'instituicao_comunidade') {
      return (
        <label key="instituicao_comunidade">
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <input
            type="text"
            required={campo.obrigatorio}
            value={instituicao}
            onChange={(e) => setInstituicao(e.target.value)}
            placeholder="Nome da instituição ou comunidade"
          />
        </label>
      );
    }
    if (campo.chave === 'telefone') {
      return (
        <label key="telefone">
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <input
            type="tel"
            required={campo.obrigatorio}
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            placeholder="(00) 00000-0000"
          />
        </label>
      );
    }
    if (campo.chave === 'email') {
      return (
        <label key="email">
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <input
            type="email"
            required={campo.obrigatorio}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@email.com"
          />
        </label>
      );
    }
    if (campo.chave === 'areas_atuacao') {
      const opcoes = formulario.opcoes_area_atuacao ?? [];
      if (opcoes.length === 0) return null;
      return (
        <section key="areas_atuacao" className="inscricao-publica__section">
          <h3>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</h3>
          <p className="inscricao-publica__hint">Selecione a(s) área(s) que melhor descrevem sua atuação.</p>
          <div className="inscricao-publica__checkboxes">
            {opcoes.map((opcao) => (
              <label key={opcao} className={`inscricao-publica__check ${areasAtuacao.includes(opcao) ? 'is-checked' : ''}`}>
                <input type="checkbox" checked={areasAtuacao.includes(opcao)} onChange={() => toggleArea(opcao)} />
                <span>{opcao}</span>
              </label>
            ))}
            <div className="inscricao-publica__outro">
              <label className={`inscricao-publica__check ${areaOutro ? 'is-checked' : ''}`}>
                <input type="checkbox" checked={Boolean(areaOutro)} onChange={(e) => { if (!e.target.checked) setAreaOutro(''); }} readOnly />
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
      );
    }
    if (campo.chave === 'representacoes') {
      const opcoes = formulario.opcoes_representacao ?? [];
      if (opcoes.length === 0) return null;
      return (
        <section key="representacoes" className="inscricao-publica__section">
          <h3>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</h3>
          <p className="inscricao-publica__hint">Assinale a representação da qual faz parte.</p>
          <div className="inscricao-publica__checkboxes">
            {opcoes.map((opcao) => (
              <label key={opcao} className={`inscricao-publica__check ${representacoes.includes(opcao) ? 'is-checked' : ''}`}>
                <input type="checkbox" checked={representacoes.includes(opcao)} onChange={() => toggleRep(opcao)} />
                <span>{opcao}</span>
              </label>
            ))}
            <div className="inscricao-publica__outro">
              <label className={`inscricao-publica__check ${repOutro ? 'is-checked' : ''}`}>
                <input type="checkbox" checked={Boolean(repOutro)} onChange={(e) => { if (!e.target.checked) setRepOutro(''); }} readOnly />
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
      );
    }
    return null;
  };

  const renderCampoCustom = (campo: CampoFormulario) => {
    const valor = valoresExtras[campo.chave];

    if (campo.tipo === 'checkbox_group') {
      const opcoes = campo.opcoes ?? [];
      const selecionados = (valor as string[] | undefined) ?? [];
      return (
        <section key={campo.chave} className="inscricao-publica__section">
          <h3>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</h3>
          <div className="inscricao-publica__checkboxes">
            {opcoes.map((opcao) => (
              <label key={opcao} className={`inscricao-publica__check ${selecionados.includes(opcao) ? 'is-checked' : ''}`}>
                <input type="checkbox" checked={selecionados.includes(opcao)} onChange={() => toggleExtraCheckbox(campo.chave, opcao)} />
                <span>{opcao}</span>
              </label>
            ))}
          </div>
        </section>
      );
    }

    if (campo.tipo === 'select') {
      const opcoes = campo.opcoes ?? [];
      return (
        <label key={campo.chave}>
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <select
            required={campo.obrigatorio}
            value={(valor as string | undefined) ?? ''}
            onChange={(e) => setExtraValor(campo.chave, e.target.value)}
          >
            <option value="">Selecione...</option>
            {opcoes.map((op) => <option key={op} value={op}>{op}</option>)}
          </select>
        </label>
      );
    }

    if (campo.tipo === 'textarea') {
      return (
        <label key={campo.chave} className="full">
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <textarea
            required={campo.obrigatorio}
            rows={4}
            value={(valor as string | undefined) ?? ''}
            onChange={(e) => setExtraValor(campo.chave, e.target.value)}
            placeholder={campo.label}
          />
        </label>
      );
    }

    if (campo.tipo === 'file') {
      return (
        <label key={campo.chave} className="full">
          <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
          <input
            type="file"
            required={campo.obrigatorio}
            onChange={(e) => setExtraArquivo(campo.chave, e.target.files?.[0] ?? null)}
          />
        </label>
      );
    }

    return (
      <label key={campo.chave}>
        <span>{campo.label}{campo.obrigatorio && <span className="required"> *</span>}</span>
        <input
          type={campo.tipo}
          required={campo.obrigatorio}
          value={(valor as string | undefined) ?? ''}
          onChange={(e) => setExtraValor(campo.chave, e.target.value)}
          placeholder={campo.label}
        />
      </label>
    );
  };

  // Separar campos que pertencem a seção "Dados do Participante" dos que formam seções próprias
  const CHAVES_SECAO_PROPRIA = new Set(['areas_atuacao', 'representacoes']);
  const camposParticipante = camposAtivos.filter(
    (c) => c.padrao && !CHAVES_SECAO_PROPRIA.has(c.chave),
  );
  const camposSecaoPropria = camposAtivos.filter(
    (c) => CHAVES_SECAO_PROPRIA.has(c.chave),
  );
  const camposExtras = camposAtivos.filter((c) => !c.padrao);

  return (
    <div className="inscricao-publica">
      {formulario.imagem_hero_url ? (
        <>
          <header className="inscricao-publica__hero has-image">
            <img
              src={formulario.imagem_hero_url}
              alt={formulario.titulo}
              className="inscricao-publica__hero-banner-img"
            />
          </header>
          <div className="inscricao-publica__hero-info">
            <span className="inscricao-publica__chip neutral">Formulário de Inscrição</span>
            <h1>{formulario.titulo}</h1>
            {formulario.subtitulo && <h2>{formulario.subtitulo}</h2>}
            {formulario.descricao && <p>{formulario.descricao}</p>}
          </div>
        </>
      ) : (
        <header className="inscricao-publica__hero">
          <span className="inscricao-publica__chip">Formulário de Inscrição</span>
          <h1>{formulario.titulo}</h1>
          {formulario.subtitulo && <h2>{formulario.subtitulo}</h2>}
          {formulario.descricao && <p>{formulario.descricao}</p>}
        </header>
      )}

      <div className="inscricao-publica__card">
        {feedback && <div className="inscricao-publica__alert success">{feedback}</div>}
        {erro && <div className="inscricao-publica__alert danger">{erro}</div>}

        {!feedback && (
          <form className="inscricao-publica__form" onSubmit={handleSubmit}>
            {camposParticipante.length > 0 && (
              <section className="inscricao-publica__section">
                <h3>Dados do Participante</h3>
                <div className="inscricao-publica__grid">
                  {camposParticipante.map((campo) => renderCampoPadrao(campo))}
                  {camposExtras
                    .filter((c) => c.tipo !== 'checkbox_group')
                    .map((campo) => renderCampoCustom(campo))}
                </div>
              </section>
            )}

            {camposSecaoPropria.map((campo) => renderCampoPadrao(campo))}

            {camposExtras
              .filter((c) => c.tipo === 'checkbox_group')
              .map((campo) => renderCampoCustom(campo))}

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
