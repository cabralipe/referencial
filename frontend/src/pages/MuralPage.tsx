import { FormEvent, MouseEvent, useMemo, useState } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAuth } from '@/context/AuthContext';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useBlocos, useMidias } from '@/hooks/useBiblioteca';
import { useMural, useRegisterMuralDownload, useSubmitMuralFile } from '@/hooks/useMural';

import './MuralPage.css';

type MuralItem =
  | {
    kind: 'mural';
    id: string;
    titulo: string;
    conteudo_html: string;
    link_url?: string | null;
    anexos?: Array<{ titulo?: string; url?: string }>;
    modalidade?: 'aviso' | 'recebimento_arquivo' | string;
    fixado?: boolean;
    position?: number;
    ordem?: number;
    gt_ids?: number[];
    criado_por?: { nome?: string | null };
    envios_arquivo?: Array<{
      id: number;
      gt_id?: number | null;
      gt_nome?: string | null;
      arquivo_url: string;
      nome_arquivo: string;
      updated_at: string;
    }>;
    updated_at: string;
  }
  | {
    kind: 'bloco';
    id: string;
    titulo: string;
    conteudo_html: string;
    updated_at: string;
  }
  | {
    kind: 'midia';
    id: string;
    titulo: string;
    descricao?: string | null;
    link_url: string;
    updated_at: string;
  };

export function MuralPage() {
  const { user } = useAuth();
  const { data: posts, isLoading } = useMural();
  const { data: midias, isLoading: midiasLoading } = useMidias();
  const { data: blocos, isLoading: blocosLoading } = useBlocos();
  const { gtOptions } = useAvailableGts();
  const submitMuralFile = useSubmitMuralFile();
  const registerMuralDownload = useRegisterMuralDownload();

  const [selectedFiles, setSelectedFiles] = useState<Record<string, File | null>>({});
  const [selectedGtIds, setSelectedGtIds] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [activePostId, setActivePostId] = useState<string | null>(null);

  const ordered = useMemo<MuralItem[]>(() => {
    const muralItems: MuralItem[] = (posts ?? []).map((post) => ({
      kind: 'mural',
      id: post.id,
      titulo: post.titulo,
      conteudo_html: post.conteudo_html,
      link_url: post.link_url,
      anexos: post.anexos,
      modalidade: post.modalidade,
      fixado: post.fixado,
      position: post.position,
      ordem: post.ordem,
      gt_ids: post.gt_ids,
      criado_por: post.criado_por,
      envios_arquivo: post.envios_arquivo,
      updated_at: post.updated_at,
    }));
    const blocoItems: MuralItem[] = (blocos ?? []).map((bloco) => ({
      kind: 'bloco',
      id: `bloco-${bloco.id}`,
      titulo: bloco.titulo,
      conteudo_html: bloco.conteudo_html,
      updated_at: bloco.updated_at,
    }));
    const midiaItems: MuralItem[] = (midias ?? []).map((midia) => ({
      kind: 'midia',
      id: `midia-${midia.id}`,
      titulo: midia.titulo || 'Link da biblioteca',
      descricao: midia.descricao,
      link_url: midia.url,
      updated_at: midia.created_at,
    }));
    return [...muralItems, ...blocoItems, ...midiaItems].sort((a, b) => {
      const fixA = a.kind === 'mural' && a.fixado ? 1 : 0;
      const fixB = b.kind === 'mural' && b.fixado ? 1 : 0;
      if (fixA !== fixB) return fixB - fixA;
      const positionA = a.kind === 'mural' ? (a.position ?? a.ordem ?? 0) : Infinity;
      const positionB = b.kind === 'mural' ? (b.position ?? b.ordem ?? 0) : Infinity;
      if (positionA !== positionB) return positionA - positionB;
      if (a.kind === 'mural' && b.kind === 'mural') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [posts, blocos, midias]);

  const getEligibleGts = (item: Extract<MuralItem, { kind: 'mural' }>) => {
    if (!item.gt_ids || item.gt_ids.length === 0) {
      return gtOptions;
    }
    return gtOptions.filter((gt) => item.gt_ids?.includes(gt.id));
  };

  const handleSubmitFile = async (event: FormEvent<HTMLFormElement>, item: Extract<MuralItem, { kind: 'mural' }>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const arquivo = selectedFiles[item.id];
    if (!arquivo) {
      setFeedback((prev) => ({ ...prev, [item.id]: 'Selecione um arquivo para enviar.' }));
      return;
    }

    const eligibleGts = getEligibleGts(item);
    const gtSelecionado =
      selectedGtIds[item.id] || (eligibleGts.length === 1 ? String(eligibleGts[0].id) : '');
    if (!gtSelecionado) {
      setFeedback((prev) => ({ ...prev, [item.id]: 'Selecione o GT responsável pelo envio.' }));
      return;
    }

    const payload = new FormData();
    payload.append('gt_id', gtSelecionado);
    payload.append('arquivo', arquivo);

    setActivePostId(item.id);
    setFeedback((prev) => ({ ...prev, [item.id]: '' }));
    try {
      await submitMuralFile.mutateAsync({ id: item.id, payload });
      setSelectedFiles((prev) => ({ ...prev, [item.id]: null }));
      setFeedback((prev) => ({ ...prev, [item.id]: 'Arquivo enviado com sucesso.' }));
      formElement.reset();
    } catch (error) {
      setFeedback((prev) => ({
        ...prev,
        [item.id]: error instanceof Error ? error.message : 'Não foi possível enviar o arquivo.',
      }));
    } finally {
      setActivePostId(null);
    }
  };

  const handleOpenAttachment = async (
    event: MouseEvent<HTMLAnchorElement>,
    item: Extract<MuralItem, { kind: 'mural' }>,
    anexoIndex: number,
    fallbackUrl?: string,
  ) => {
    event.preventDefault();
    try {
      const result = await registerMuralDownload.mutateAsync({ id: item.id, anexoIndex });
      const url = result.url || fallbackUrl;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
    } catch {
      if (fallbackUrl) {
        window.open(fallbackUrl, '_blank', 'noopener,noreferrer');
      }
    }
  };

  if (isLoading || midiasLoading || blocosLoading) {
    return <FullPageLoader message="Carregando mural..." />;
  }

  return (
    <div className="mural">
      <PageHeader title="Mural" description="Acompanhe os avisos e documentos publicados pela administração." />

      <div className="mural__grid">
        {ordered.map((item) => {
          if (item.kind === 'midia') {
            const descricao = item.descricao?.trim() || item.link_url;
            return (
              <Card key={item.id}>
                <div className="mural__card">
                  <header>
                    <div>
                      <h2>{item.titulo}</h2>
                      <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                    </div>
                  </header>
                  <p>{descricao}</p>
                  <a className="mural__link" href={item.link_url} target="_blank" rel="noreferrer">
                    Abrir link
                  </a>
                </div>
              </Card>
            );
          }

          if (item.kind === 'bloco') {
            return (
              <Card key={item.id}>
                <div className="mural__card">
                  <header>
                    <div>
                      <h2>{item.titulo}</h2>
                      <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                    </div>
                  </header>
                  <div dangerouslySetInnerHTML={{ __html: item.conteudo_html }} />
                </div>
              </Card>
            );
          }

          const eligibleGts = getEligibleGts(item);
          const canSubmitFile = user?.role === 'membro_gt' && item.modalidade === 'recebimento_arquivo' && eligibleGts.length > 0;

          return (
            <Card key={item.id}>
              <div className="mural__card">
                <header>
                  <div>
                    <h2>{item.titulo}</h2>
                    <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                  </div>
                  <div className="mural__meta">
                    {item.modalidade === 'recebimento_arquivo' && <span className="mural__badge mural__badge--info">Recebe arquivo</span>}
                    {item.fixado && <span className="mural__badge">Fixado</span>}
                  </div>
                </header>
                <div dangerouslySetInnerHTML={{ __html: item.conteudo_html }} />
                {item.link_url && (
                  <a className="mural__link" href={item.link_url} target="_blank" rel="noreferrer">
                    Abrir link
                  </a>
                )}
                {item.anexos && item.anexos.length > 0 && (
                  <div className="mural__anexos">
                    {item.anexos.map((anexo, index) => (
                      <a
                        key={`${item.id}-${index}`}
                        href={anexo.url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(event) => void handleOpenAttachment(event, item, index, anexo.url)}
                      >
                        {anexo.titulo || 'Anexo'}
                      </a>
                    ))}
                  </div>
                )}
                {canSubmitFile && (
                  <form className="mural__upload-form" onSubmit={(event) => handleSubmitFile(event, item)}>
                    <h3>Enviar arquivo</h3>
                    {eligibleGts.length > 1 && (
                      <label>
                        <span>GT</span>
                        <select
                          value={selectedGtIds[item.id] ?? ''}
                          onChange={(event) =>
                            setSelectedGtIds((prev) => ({
                              ...prev,
                              [item.id]: event.target.value,
                            }))
                          }
                        >
                          <option value="">Selecione</option>
                          {eligibleGts.map((gt) => (
                            <option key={gt.id} value={gt.id}>
                              {gt.displayName}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <label>
                      <span>Arquivo</span>
                      <input
                        type="file"
                        onChange={(event) =>
                          setSelectedFiles((prev) => ({
                            ...prev,
                            [item.id]: event.target.files?.[0] ?? null,
                          }))
                        }
                      />
                    </label>
                    <Button type="submit" variant="secondary" disabled={submitMuralFile.isPending && activePostId === item.id}>
                      {submitMuralFile.isPending && activePostId === item.id ? 'Enviando...' : 'Enviar arquivo'}
                    </Button>
                    {feedback[item.id] && <p className="mural__feedback">{feedback[item.id]}</p>}
                  </form>
                )}
                {item.envios_arquivo && item.envios_arquivo.length > 0 && (
                  <div className="mural__envios">
                    <h3>Seus envios</h3>
                    {item.envios_arquivo.map((envio) => (
                      <a key={envio.id} href={envio.arquivo_url} target="_blank" rel="noreferrer">
                        {envio.gt_nome ? `${envio.gt_nome} · ` : ''}
                        {envio.nome_arquivo}
                      </a>
                    ))}
                  </div>
                )}
                {item.criado_por?.nome && <p className="mural__autor">Publicado por {item.criado_por.nome}</p>}
              </div>
            </Card>
          );
        })}
        {ordered.length === 0 && <p className="mural__empty">Nenhum aviso publicado ainda.</p>}
      </div>
    </div>
  );
}
