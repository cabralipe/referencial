import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { useApiClient } from '@/api/client';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateExportJob, useDownloadExport } from '@/hooks/useExportJobs';
import { fetchAllPaginated } from '@/utils/pagination';
import type { PaginatedResponse, Resposta } from '@/api/types';

import './RedatorProductionPage.css';

interface Redator {
    id: number;
    nome: string;
    email: string;
    role: string;
    is_active: boolean;
}

export function RedatorProductionPage() {
    const client = useApiClient();
    const baixarExportacao = useDownloadExport();
    const [selectedRedator, setSelectedRedator] = useState<Redator | null>(null);
    const [search, setSearch] = useState('');
    const [exportFeedback, setExportFeedback] = useState('');

    // 1. Buscar todos os usuários redatores (articuladores)
    const { data: redatores = [], isLoading: loadingRedatores } = useQuery({
        queryKey: ['usuarios', 'redatores'],
        queryFn: async () => {
            return fetchAllPaginated<Redator>(client.get, '/usuarios/lookup', {
                query: { role: 'articulador', page_size: 100 },
            });
        },
    });

    // 2. Buscar todas as respostas para calcular estatísticas
    const { data: respostas = [], isLoading: loadingRespostas } = useQuery({
        queryKey: ['respostas', 'all'],
        queryFn: async () => {
            return fetchAllPaginated<Resposta>(client.get, '/respostas', {
                query: { page_size: 500 },
            });
        },
    });

    // 3. Processar estatísticas
    const stats = useMemo(() => {
        const map = new Map<number, number>();
        respostas.forEach((r) => {
            if (r.autor) {
                map.set(r.autor, (map.get(r.autor) || 0) + 1);
            }
        });
        return map;
    }, [respostas]);

    // 4. Filtrar lista de redatores
    const filteredRedatores = useMemo(() => {
        // Deduplicate redatores by ID to prevent key warnings
        const uniqueRedatores = Array.from(new Map(redatores.map(item => [item.id, item])).values());

        return uniqueRedatores.filter((r) =>
            r.nome.toLowerCase().includes(search.toLowerCase()) ||
            r.email.toLowerCase().includes(search.toLowerCase())
        );
    }, [redatores, search]);

    // 5. Obter respostas do redator selecionado
    const redatorRespostas = useMemo(() => {
        if (!selectedRedator) return [];
        return respostas.filter((r) => r.autor === selectedRedator.id);
    }, [selectedRedator, respostas]);

    const handleExportPdf = async () => {
        if (!selectedRedator) return;
        setExportFeedback('Gerando PDF...');

        // Construir HTML simples para o relatório
        const now = new Date().toLocaleDateString('pt-BR');
        const htmlContent = `
      <div style="font-family: sans-serif; padding: 20px;">
        <h1 style="color: #1e3a8a;">Relatório de Produção - ${selectedRedator.nome}</h1>
        <p><strong>Email:</strong> ${selectedRedator.email}</p>
        <p><strong>Gerado em:</strong> ${now}</p>
        <p><strong>Total de textos:</strong> ${redatorRespostas.length}</p>
        <hr style="margin: 20px 0; border: 0; border-top: 1px solid #ccc;">
        
        ${redatorRespostas.map(r => `
          <div style="margin-bottom: 30px; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px;">
            <div style="background: #f3f4f6; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
              <strong>GT:</strong> ${r.gt_nome || 'N/A'} <br>
              <strong>Pergunta:</strong> ${r.pergunta_texto || `Pergunta #${r.pergunta}`}
            </div>
            <div>${r.conteudo_html}</div>
          </div>
        `).join('')}
      </div>
    `;

        try {
            const blob = await baixarExportacao.mutateAsync({
                alvoTipo: 'relatorio', // Tipo válido: RELATORIO
                alvoId: String(selectedRedator.id),
                formato: 'pdf',
                payloadJson: {
                    titulo: `Produção - ${selectedRedator.nome}`,
                    conteudo_html: htmlContent,
                    modo: 'completo',
                },
            });

            // Trigger download
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `producao_${selectedRedator.nome.replace(/\s+/g, '_').toLowerCase()}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);

            setExportFeedback('Download iniciado com sucesso!');
        } catch (err) {
            setExportFeedback('Erro ao gerar PDF.');
            console.error(err);
        }
    };

    if (loadingRedatores || loadingRespostas) {
        return <FullPageLoader message="Carregando dados de produção..." />;
    }

    return (
        <div className="redator-production">
            <PageHeader
                title="Produção por Redator"
                description="Acompanhe o volume de respostas e exporte portfólios individuais."
                actions={
                    <Link to="/admin/console" className="btn-back">
                        Voltar ao Console
                    </Link>
                }
            />

            <div className="redator-production__layout">
                <aside className="redator-production__sidebar">
                    <Card>
                        <div className="redator-production__search">
                            <input
                                type="search"
                                placeholder="Buscar redator..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                        <div className="redator-production__list">
                            {filteredRedatores.map((redator) => (
                                <button
                                    key={redator.id}
                                    className={`redator-item ${selectedRedator?.id === redator.id ? 'active' : ''}`}
                                    onClick={() => setSelectedRedator(redator)}
                                >
                                    <div className="redator-item__info">
                                        <strong>{redator.nome}</strong>
                                        <small>{redator.email}</small>
                                    </div>
                                    <span className="redator-item__badge">
                                        {stats.get(redator.id) || 0}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </Card>
                </aside>

                <main className="redator-production__content">
                    {selectedRedator ? (
                        <Card>
                            <div className="redator-detail__header">
                                <div>
                                    <h2>{selectedRedator.nome}</h2>
                                    <p>{stats.get(selectedRedator.id) || 0} textos produzidos</p>
                                </div>
                                <div className="redator-detail__actions">
                                    <button
                                        onClick={handleExportPdf}
                                        disabled={baixarExportacao.isPending}
                                        className="btn-primary"
                                    >
                                        {baixarExportacao.isPending ? 'Baixando...' : 'Baixar PDF'}
                                    </button>
                                </div>
                            </div>
                            {exportFeedback && <div className="feedback-message">{exportFeedback}</div>}

                            <div className="redator-detail__feed">
                                {redatorRespostas.length === 0 ? (
                                    <p className="empty-state">Nenhum texto produzido por este redator.</p>
                                ) : (
                                    redatorRespostas.map((resposta) => (
                                        <div key={resposta.id} className="resposta-preview">
                                            <div className="resposta-preview__meta">
                                                <span className="badge-gt">{resposta.gt_nome || 'GT Desconhecido'}</span>
                                                <span className="date">{new Date(resposta.updated_at).toLocaleDateString()}</span>
                                            </div>
                                            <div className="resposta-preview__question">
                                                {resposta.pergunta_texto || `Pergunta ID: ${resposta.pergunta}`}
                                            </div>
                                            <div
                                                className="resposta-preview__body"
                                                dangerouslySetInnerHTML={{ __html: resposta.conteudo_html }}
                                            />
                                        </div>
                                    ))
                                )}
                            </div>
                        </Card>
                    ) : (
                        <div className="empty-selection">
                            <Card>
                                <p>Selecione um redator ao lado para ver os detalhes.</p>
                            </Card>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}
