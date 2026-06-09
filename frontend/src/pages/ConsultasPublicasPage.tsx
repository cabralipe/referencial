import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ApiError } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import {
  useConsultasPublicas,
  useCriarConsultaPublica,
  useExcluirConsultaPublica,
  useManifestacoesConsulta,
  useEditarConsultaPublica,
} from '@/hooks/useConsultasPublicas';
import {
  useFormulariosInscricao,
  useCriarFormularioInscricao,
  useEditarFormularioInscricao,
  useExcluirFormularioInscricao,
  useInscricoesFormulario,
} from '@/hooks/useFormulariosInscricao';
import type { CampoFormulario, CampoFormularioTipo, ConsultaPublica, FormularioInscricao, InscricaoPublica } from '@/api/types';

import './ConsultasPublicasPage.css';

interface PerguntaFormItem {
  pergunta: string;
  opcoesTexto: string; // raw textarea value (one option per line)
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) return value;
  return new Date(year, month - 1, day).toLocaleDateString('pt-BR');
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function exportarCsv(inscricoes: InscricaoPublica[], filename: string) {
  const cabecalho = [
    'ID', 'Nome Completo', 'Instituição / Comunidade', 'Telefone', 'E-mail',
    'Áreas de Atuação', 'Área Outro', 'Representações', 'Representação Outro', 'Data',
  ];
  const linhas = inscricoes.map((i) => [
    i.id,
    i.nome_completo,
    i.instituicao_comunidade,
    i.telefone,
    i.email,
    (i.areas_atuacao || []).join('; '),
    i.area_atuacao_outro,
    (i.representacoes || []).join('; '),
    i.representacao_outro,
    new Date(i.created_at).toLocaleString('pt-BR'),
  ]);
  const conteudo = [cabecalho, ...linhas]
    .map((row) => row.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(','))
    .join('\n');
  const blob = new Blob(['﻿' + conteudo], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportarPdf(inscricoes: InscricaoPublica[], titulo: string) {
  const esc = (s: string | number | undefined | null) =>
    String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  const datas = inscricoes.map((i) => new Date(i.created_at));
  const minData = datas.length ? new Date(Math.min(...datas.map((d) => d.getTime()))) : null;
  const maxData = datas.length ? new Date(Math.max(...datas.map((d) => d.getTime()))) : null;
  const periodo = minData && maxData
    ? `${minData.toLocaleDateString('pt-BR')} a ${maxData.toLocaleDateString('pt-BR')}`
    : '—';
  const ultimaAtualizacao = maxData ? maxData.toLocaleString('pt-BR') : '—';

  const contarOcorrencias = (lista: string[]) => {
    const map: Record<string, number> = {};
    lista.forEach((v) => { map[v] = (map[v] ?? 0) + 1; });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  };

  const todasReps = inscricoes.flatMap((i) =>
    [...(i.representacoes || []), ...(i.representacao_outro ? [`Outro: ${i.representacao_outro}`] : [])],
  );
  const todasAreas = inscricoes.flatMap((i) =>
    [...(i.areas_atuacao || []), ...(i.area_atuacao_outro ? [`Outro: ${i.area_atuacao_outro}`] : [])],
  );

  const pillsReps = contarOcorrencias(todasReps.filter(Boolean))
    .map(([k, v]) => `<span class="pill"><strong>${esc(k)}</strong><em>${v}</em></span>`)
    .join('\n');
  const pillsAreas = contarOcorrencias(todasAreas.filter(Boolean))
    .map(([k, v]) => `<span class="pill"><strong>${esc(k)}</strong><em>${v}</em></span>`)
    .join('\n');

  const linhasTabela = inscricoes.map((i) => `
    <tr>
      <td class="center id">${i.id}</td>
      <td class="name">${esc(i.nome_completo)}</td>
      <td>${esc(i.instituicao_comunidade)}</td>
      <td class="nowrap">${esc(i.telefone)}</td>
      <td class="email">${esc(i.email)}</td>
      <td>${esc([...(i.areas_atuacao || []), ...(i.area_atuacao_outro ? [`Outro: ${i.area_atuacao_outro}`] : [])].join('; '))}</td>
      <td>${esc([...(i.representacoes || []), ...(i.representacao_outro ? [`Outro: ${i.representacao_outro}`] : [])].join('; '))}</td>
      <td class="date-cell">${new Date(i.created_at).toLocaleString('pt-BR')}</td>
    </tr>`).join('');

  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Relatório de Inscrições – ${esc(titulo)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    @page { size: A4 portrait; margin: 12mm 14mm 12mm 10mm; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, Helvetica, sans-serif; color: #1f2933; background: #ffffff; font-size: 9.6px; line-height: 1.22; }
    .page { width: 100%; margin: 0 auto; }
    header { border-bottom: 2px solid #243b53; padding-bottom: 8px; margin-bottom: 10px; }
    .kicker { font-size: 9px; letter-spacing: .08em; text-transform: uppercase; color: #52606d; margin-bottom: 2px; font-weight: 700; }
    h1 { margin: 0; font-size: 20px; color: #102a43; line-height: 1.1; }
    .subtitle { margin-top: 4px; color: #334e68; font-size: 10.5px; }
    .meta-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 10px 0 8px 0; }
    .meta-card { border: 1px solid #bcccdc; border-radius: 8px; padding: 7px 8px; background: #f8fafc; }
    .meta-label { display: block; color: #627d98; font-size: 8.5px; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; font-weight: 700; }
    .meta-value { display: block; color: #102a43; font-size: 14px; font-weight: 700; }
    .section-title { font-size: 12px; margin: 11px 0 5px 0; color: #102a43; border-left: 4px solid #486581; padding-left: 6px; }
    .pills { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 7px; }
    .pill { display: inline-flex; align-items: center; gap: 5px; border: 1px solid #d9e2ec; border-radius: 999px; padding: 3px 6px; background: #ffffff; color: #243b53; max-width: 100%; }
    .pill strong { font-size: 8.6px; font-weight: 700; }
    .pill em { font-style: normal; font-size: 8.1px; background: #e6eef6; color: #102a43; padding: 1px 5px; border-radius: 999px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; page-break-inside: auto; }
    thead { display: table-header-group; }
    tr { page-break-inside: avoid; page-break-after: auto; }
    th { background: #243b53; color: #ffffff; font-weight: 700; text-align: left; padding: 5px 4px; border: 1px solid #243b53; font-size: 8px; vertical-align: middle; }
    td { border: 1px solid #d9e2ec; padding: 3.5px; vertical-align: top; overflow-wrap: anywhere; word-break: normal; }
    tbody tr:nth-child(even) td { background: #f8fafc; }
    .center { text-align: center; }
    .nowrap { white-space: nowrap; }
    .date-cell { white-space: normal; font-size: 8.1px; line-height: 1.12; overflow-wrap: normal; word-break: keep-all; padding-right: 6px; }
    .id { font-weight: 700; color: #102a43; }
    .name { font-weight: 700; color: #102a43; }
    .email { font-size: 8.3px; }
    .footer { margin-top: 8px; padding-top: 5px; border-top: 1px solid #d9e2ec; color: #627d98; font-size: 8.5px; display: flex; justify-content: space-between; gap: 10px; }
    .no-print { display: block; margin: 10px 0; padding: 8px; border: 1px solid #d9e2ec; border-radius: 8px; background: #f8fafc; color: #334e68; font-size: 12px; }
    .print-button { border: 0; border-radius: 6px; padding: 8px 12px; background: #243b53; color: #fff; font-weight: 700; cursor: pointer; }
    @media print { .no-print { display: none !important; } body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } a { color: inherit; text-decoration: none; } }
    @media screen { body { background: #e5eaf0; padding: 18px; } .page { max-width: 210mm; background: #fff; padding: 12mm 10mm; box-shadow: 0 10px 35px rgba(16,42,67,.18); } }
  </style>
</head>
<body>
  <main class="page">
    <div class="no-print">
      <button class="print-button" onclick="window.print()">Imprimir / Salvar em PDF</button>
      &nbsp;Layout configurado para A4. Na impressão, selecione papel A4 e margens padrão ou personalizadas.
    </div>
    <header>
      <div class="kicker">Relatório para impressão</div>
      <h1>Lista de Inscrições</h1>
      <div class="subtitle">${esc(titulo)}</div>
    </header>
    <section class="meta-grid" aria-label="Resumo geral">
      <div class="meta-card"><span class="meta-label">Total de inscrições</span><span class="meta-value">${inscricoes.length}</span></div>
      <div class="meta-card"><span class="meta-label">Período</span><span class="meta-value">${esc(periodo)}</span></div>
      <div class="meta-card"><span class="meta-label">Última atualização registrada</span><span class="meta-value">${esc(ultimaAtualizacao)}</span></div>
    </section>
    <h2 class="section-title">Resumo por representação</h2>
    <div class="pills">${pillsReps || '<em>—</em>'}</div>
    <h2 class="section-title">Resumo por área de atuação</h2>
    <div class="pills">${pillsAreas || '<em>—</em>'}</div>
    <h2 class="section-title">Relação completa dos inscritos</h2>
    <table>
      <colgroup>
        <col style="width:4%"><col style="width:17%"><col style="width:18%"><col style="width:10%">
        <col style="width:15%"><col style="width:10%"><col style="width:14%"><col style="width:12%">
      </colgroup>
      <thead>
        <tr>
          <th class="center">ID</th><th>Nome completo</th><th>Instituição / Comunidade</th>
          <th>Telefone</th><th>E-mail</th><th>Área</th><th>Representação</th><th>Data</th>
        </tr>
      </thead>
      <tbody>${linhasTabela}</tbody>
    </table>
    <div class="footer">
      <span>Documento preparado para impressão em A4.</span>
      <span>Total: ${inscricoes.length} inscrições.</span>
    </div>
  </main>
</body>
</html>`;

  const win = window.open('', '_blank');
  if (win) {
    win.document.write(html);
    win.document.close();
  }
}

// ── Formulários de Inscrição tab ──────────────────────────────────────────────

const AREAS_PADRAO = ['Educação', 'Saúde', 'Assistência Social', 'Cultura', 'Gestão Pública', 'Sociedade Civil'];
const REPS_PADRAO = [
  'Poder Executivo', 'Poder Legislativo', 'Conselho Municipal de Educação – CME',
  'Ministério Público', 'Coordenação Geral do Referencial Curricular', 'Articulador(a) do Território',
  'GT Educação Infantil', 'GT Ensino Fundamental', 'GT Educação de Jovens e Adultos – EJA',
  'GT Educação Especial', 'GT BNCC Computação', 'Gestor(a) Escolar', 'Professor(a)',
  'Estudante', 'Família / Responsável', 'Representação Indígena', 'Representação Quilombola',
  'Comunidade do Campo', 'Assentamento',
];

const CAMPOS_PADRAO: CampoFormulario[] = [
  { chave: 'nome_completo', label: 'Nome Completo', tipo: 'text', obrigatorio: true, ordem: 1, ativo: true, padrao: true },
  { chave: 'instituicao_comunidade', label: 'Instituição / Comunidade', tipo: 'text', obrigatorio: false, ordem: 2, ativo: true, padrao: true },
  { chave: 'telefone', label: 'Telefone', tipo: 'tel', obrigatorio: false, ordem: 3, ativo: true, padrao: true },
  { chave: 'email', label: 'E-mail', tipo: 'email', obrigatorio: false, ordem: 4, ativo: true, padrao: true },
  { chave: 'areas_atuacao', label: 'Área de Atuação', tipo: 'checkbox_group', obrigatorio: false, ordem: 5, ativo: true, padrao: true },
  { chave: 'representacoes', label: 'Representação', tipo: 'checkbox_group', obrigatorio: false, ordem: 6, ativo: true, padrao: true },
];

const TIPO_LABELS: Record<CampoFormularioTipo, string> = {
  text: 'Texto curto',
  email: 'E-mail',
  tel: 'Telefone',
  textarea: 'Texto longo',
  select: 'Seleção (dropdown)',
  checkbox_group: 'Caixas de seleção',
  number: 'Número',
  file: 'Upload de arquivo',
};

interface GerenciadorCamposProps {
  campos: CampoFormulario[];
  onChange: (campos: CampoFormulario[]) => void;
}

function GerenciadorCampos({ campos, onChange }: GerenciadorCamposProps) {
  const [editandoCampo, setEditandoCampo] = useState<CampoFormulario | null>(null);
  const [editandoIndex, setEditandoIndex] = useState<number | null>(null);

  const moverCampo = (index: number, direcao: -1 | 1) => {
    const alvo = index + direcao;
    if (alvo < 0 || alvo >= campos.length) return;
    const novos = [...campos];
    [novos[index], novos[alvo]] = [novos[alvo], novos[index]];
    novos.forEach((c, i) => { c.ordem = i + 1; });
    onChange(novos);
  };

  const toggleAtivo = (index: number) => {
    const novos = campos.map((c, i) => i === index ? { ...c, ativo: !c.ativo } : c);
    onChange(novos);
  };

  const excluirCampo = (index: number) => {
    onChange(campos.filter((_, i) => i !== index));
  };

  const abrirEdicaoCampo = (campo: CampoFormulario, index: number) => {
    setEditandoCampo({ ...campo, opcoes: campo.opcoes ? [...campo.opcoes] : [] });
    setEditandoIndex(index);
  };

  const adicionarNovoCampo = () => {
    const novoCampo: CampoFormulario = {
      chave: `campo_${Date.now()}`,
      label: 'Novo campo',
      tipo: 'text',
      obrigatorio: false,
      ordem: campos.length + 1,
      ativo: true,
      padrao: false,
    };
    setEditandoCampo(novoCampo);
    setEditandoIndex(campos.length);
  };

  const salvarCampoEditado = () => {
    if (!editandoCampo) return;
    const novos = [...campos];
    if (editandoIndex !== null && editandoIndex < campos.length) {
      novos[editandoIndex] = editandoCampo;
    } else {
      novos.push(editandoCampo);
    }
    novos.forEach((c, i) => { c.ordem = i + 1; });
    onChange(novos);
    setEditandoCampo(null);
    setEditandoIndex(null);
  };

  return (
    <div style={{ marginTop: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <strong style={{ fontSize: '0.9rem' }}>Campos do formulário</strong>
        <button type="button" className="ghost" onClick={adicionarNovoCampo}
          style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', borderRadius: '6px', border: '1px solid var(--color-border)', cursor: 'pointer' }}>
          + Adicionar campo
        </button>
      </div>

      {campos.length === 0 && (
        <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
          Nenhum campo configurado. Clique em "+ Adicionar campo" ou o formulário usará os campos padrão.
        </p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {campos.map((campo, index) => (
          <div key={campo.chave}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 0.75rem', borderRadius: '6px',
              border: '1px solid var(--color-border)',
              background: campo.ativo ? 'var(--color-surface)' : '#f5f5f5',
              opacity: campo.ativo ? 1 : 0.6,
            }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginRight: '4px' }}>
              <button type="button" onClick={() => moverCampo(index, -1)} disabled={index === 0}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '1px 4px', fontSize: '0.65rem', lineHeight: 1, color: index === 0 ? '#ccc' : 'inherit' }}>▲</button>
              <button type="button" onClick={() => moverCampo(index, 1)} disabled={index === campos.length - 1}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '1px 4px', fontSize: '0.65rem', lineHeight: 1, color: index === campos.length - 1 ? '#ccc' : 'inherit' }}>▼</button>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {campo.label}
                {campo.obrigatorio && <span style={{ color: '#dc2626', marginLeft: '4px' }}>*</span>}
                {campo.padrao && <span style={{ fontSize: '0.7rem', background: '#e0f2fe', color: '#0369a1', padding: '1px 5px', borderRadius: '4px', marginLeft: '6px' }}>padrão</span>}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                {TIPO_LABELS[campo.tipo] ?? campo.tipo} — chave: {campo.chave}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.375rem', flexShrink: 0 }}>
              <button type="button" onClick={() => toggleAtivo(index)}
                style={{ padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--color-border)', background: 'none', cursor: 'pointer', fontSize: '0.75rem' }}>
                {campo.ativo ? 'Ocultar' : 'Mostrar'}
              </button>
              <button type="button" onClick={() => abrirEdicaoCampo(campo, index)}
                style={{ padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--color-border)', background: 'none', cursor: 'pointer', fontSize: '0.75rem' }}>
                Editar
              </button>
              {!campo.padrao && (
                <button type="button" onClick={() => excluirCampo(index)}
                  style={{ padding: '3px 8px', borderRadius: '4px', border: '1px solid #fca5a5', background: '#fff5f5', color: '#dc2626', cursor: 'pointer', fontSize: '0.75rem' }}>
                  Excluir
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {editandoCampo && (
        <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--color-border)', borderRadius: '8px', background: 'var(--color-surface)' }}>
          <strong style={{ fontSize: '0.875rem', display: 'block', marginBottom: '0.75rem' }}>
            {editandoIndex !== null && editandoIndex < campos.length ? 'Editar campo' : 'Novo campo'}
          </strong>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.8125rem' }}>
              <span>Rótulo (label)</span>
              <input
                value={editandoCampo.label}
                onChange={(e) => setEditandoCampo({ ...editandoCampo, label: e.target.value })}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '4px', border: '1px solid var(--color-border)', fontSize: '0.8125rem' }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.8125rem' }}>
              <span>Chave (identificador)</span>
              <input
                value={editandoCampo.chave}
                disabled={editandoCampo.padrao}
                onChange={(e) => setEditandoCampo({ ...editandoCampo, chave: e.target.value.replace(/\s+/g, '_').toLowerCase() })}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '4px', border: '1px solid var(--color-border)', fontSize: '0.8125rem', background: editandoCampo.padrao ? '#f5f5f5' : undefined }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.8125rem' }}>
              <span>Tipo</span>
              <select
                value={editandoCampo.tipo}
                disabled={editandoCampo.padrao}
                onChange={(e) => setEditandoCampo({ ...editandoCampo, tipo: e.target.value as CampoFormularioTipo })}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '4px', border: '1px solid var(--color-border)', fontSize: '0.8125rem', background: editandoCampo.padrao ? '#f5f5f5' : undefined }}
              >
                {(Object.entries(TIPO_LABELS) as [CampoFormularioTipo, string][]).map(([val, lbl]) => (
                  <option key={val} value={val}>{lbl}</option>
                ))}
              </select>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', paddingTop: '1.25rem' }}>
              <input
                type="checkbox"
                checked={editandoCampo.obrigatorio}
                onChange={(e) => setEditandoCampo({ ...editandoCampo, obrigatorio: e.target.checked })}
              />
              <span>Campo obrigatório</span>
            </label>
          </div>
          {(editandoCampo.tipo === 'select' || (editandoCampo.tipo === 'checkbox_group' && !editandoCampo.padrao)) && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.8125rem', marginTop: '0.75rem' }}>
              <span>Opções (uma por linha)</span>
              <textarea
                rows={4}
                value={(editandoCampo.opcoes ?? []).join('\n')}
                onChange={(e) => setEditandoCampo({ ...editandoCampo, opcoes: e.target.value.split('\n').map((l) => l.trim()).filter(Boolean) })}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '4px', border: '1px solid var(--color-border)', fontSize: '0.8125rem', resize: 'vertical' }}
              />
            </label>
          )}
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
            <button type="button" onClick={salvarCampoEditado}
              style={{ padding: '0.375rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--color-primary)', color: '#fff', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600 }}>
              Salvar campo
            </button>
            <button type="button" onClick={() => { setEditandoCampo(null); setEditandoIndex(null); }}
              style={{ padding: '0.375rem 1rem', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'none', cursor: 'pointer', fontSize: '0.8125rem' }}>
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function FormulariosInscricaoTab() {
  const { data: formularios, isLoading } = useFormulariosInscricao();
  const criarFormulario = useCriarFormularioInscricao();
  const editarFormulario = useEditarFormularioInscricao();
  const excluirFormulario = useExcluirFormularioInscricao();

  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [formularioSelecionado, setFormularioSelecionado] = useState<FormularioInscricao | null>(null);
  const [abaInscricoes, setAbaInscricoes] = useState<number | null>(null);
  const [nomeFiltro, setNomeFiltro] = useState('');
  const [nomeFiltroAplicado, setNomeFiltroAplicado] = useState('');
  const [editando, setEditando] = useState<FormularioInscricao | null>(null);
  const [heroImageFile, setHeroImageFile] = useState<File | null>(null);

  // opcoes editaveis como texto (uma por linha)
  const [areasTexto, setAreasTexto] = useState(AREAS_PADRAO.join('\n'));
  const [repsTexto, setRepsTexto] = useState(REPS_PADRAO.join('\n'));

  // campos do formulário
  const [camposConfig, setCamposConfig] = useState<CampoFormulario[]>(CAMPOS_PADRAO.map((c) => ({ ...c })));
  const [camposConfigEdicao, setCamposConfigEdicao] = useState<CampoFormulario[]>([]);

  const { data: inscricoes, isLoading: carregandoInscricoes } = useInscricoesFormulario(
    abaInscricoes ?? undefined,
    nomeFiltroAplicado,
  );

  const parseOpcoes = (texto: string) =>
    texto.split('\n').map((l) => l.trim()).filter(Boolean);

  const handleCriar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMensagem(null);
    setErro(null);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const titulo = String(form.get('titulo') ?? '').trim();
    const subtitulo = String(form.get('subtitulo') ?? '').trim();
    const descricao = String(form.get('descricao') ?? '').trim();
    const ativo = form.get('ativo') !== null;
    if (!titulo) { setErro('Informe o título.'); return; }
    try {
      await criarFormulario.mutateAsync({
        titulo,
        subtitulo: subtitulo || undefined,
        descricao: descricao || undefined,
        ativo,
        opcoes_area_atuacao: parseOpcoes(areasTexto),
        opcoes_representacao: parseOpcoes(repsTexto),
        campos_config: camposConfig,
        imagem_hero: heroImageFile || undefined,
      });
      setMensagem('Formulário criado! Compartilhe o link público para iniciar as inscrições.');
      formElement.reset();
      setHeroImageFile(null);
      setAreasTexto(AREAS_PADRAO.join('\n'));
      setRepsTexto(REPS_PADRAO.join('\n'));
      setCamposConfig(CAMPOS_PADRAO.map((c) => ({ ...c })));
    } catch (e: any) {
      setErro(e?.message ?? 'Não foi possível criar o formulário.');
    }
  };

  const handleEditar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editando) return;
    setMensagem(null);
    setErro(null);
    const form = new FormData(event.currentTarget);
    const titulo = String(form.get('titulo') ?? '').trim();
    const subtitulo = String(form.get('subtitulo') ?? '').trim();
    const descricao = String(form.get('descricao') ?? '').trim();
    const ativo = form.get('ativo') !== null;
    try {
      await editarFormulario.mutateAsync({
        id: editando.id,
        titulo,
        subtitulo,
        descricao,
        ativo,
        opcoes_area_atuacao: parseOpcoes(areasTexto),
        opcoes_representacao: parseOpcoes(repsTexto),
        campos_config: camposConfigEdicao,
        imagem_hero: heroImageFile || undefined,
      });
      setMensagem('Formulário atualizado.');
      setEditando(null);
      setHeroImageFile(null);
    } catch (e: any) {
      setErro(e?.message ?? 'Não foi possível atualizar o formulário.');
    }
  };

  const handleDelete = async (f: FormularioInscricao) => {
    if (!window.confirm(`Excluir o formulário "${f.titulo}"? Todas as inscrições serão perdidas.`)) return;
    setErro(null);
    try {
      await excluirFormulario.mutateAsync(f.id);
      setMensagem('Formulário removido.');
    } catch (e: any) {
      setErro(e?.message ?? 'Não foi possível excluir.');
    }
  };

  const handleCopyLink = async (f: FormularioInscricao) => {
    const url = f.public_url || `${window.location.origin}/inscricoes/${f.token_acesso}`;
    try {
      await navigator.clipboard.writeText(url);
      setMensagem('Link copiado!');
    } catch {
      setErro('Não foi possível copiar o link.');
    }
  };

  const abrirEdicao = (f: FormularioInscricao) => {
    setEditando(f);
    setAreasTexto((f.opcoes_area_atuacao || AREAS_PADRAO).join('\n'));
    setRepsTexto((f.opcoes_representacao || REPS_PADRAO).join('\n'));
    setCamposConfigEdicao(
      f.campos_config && f.campos_config.length > 0
        ? f.campos_config.map((c) => ({ ...c }))
        : CAMPOS_PADRAO.map((c) => ({ ...c }))
    );
  };

  if (isLoading && !formularios) return <FullPageLoader message="Carregando formulários..." />;

  return (
    <div>
      <section className="consultas-admin__form-card">
        <div className="consultas-admin__form-header">
          <div>
            <h2>Novo formulário de inscrição</h2>
            <p>Crie um formulário personalizável com link público para inscrições em audiências públicas.</p>
          </div>
          {mensagem && !editando && <span className="consultas-admin__badge success">{mensagem}</span>}
          {erro && !editando && <span className="consultas-admin__badge danger">{erro}</span>}
        </div>
        <form className="consultas-admin__form" onSubmit={handleCriar}>
          <label>
            <span>Título do evento</span>
            <input name="titulo" type="text" defaultValue="Audiência Pública do Referencial Curricular" required />
          </label>
          <label>
            <span>Subtítulo</span>
            <input name="subtitulo" type="text" defaultValue="Ficha de Inscrição" />
          </label>
          <label className="full">
            <span>Descrição (opcional)</span>
            <textarea name="descricao" rows={2} placeholder="Breve descrição do evento ou instruções para o participante" />
          </label>
          <div className="full consultas-admin__perguntas-section">
            <div className="consultas-admin__perguntas-header">
              <span>Opções de Área de Atuação (uma por linha)</span>
            </div>
            <textarea
              rows={6}
              value={areasTexto}
              onChange={(e) => setAreasTexto(e.target.value)}
              placeholder="Educação&#10;Saúde&#10;Cultura&#10;..."
              style={{ width: '100%', padding: '0.625rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontFamily: 'inherit', fontSize: '0.875rem', resize: 'vertical' }}
            />
          </div>
          <div className="full consultas-admin__perguntas-section">
            <div className="consultas-admin__perguntas-header">
              <span>Opções de Representação (uma por linha)</span>
            </div>
            <textarea
              rows={10}
              value={repsTexto}
              onChange={(e) => setRepsTexto(e.target.value)}
              placeholder="Poder Executivo&#10;Poder Legislativo&#10;..."
              style={{ width: '100%', padding: '0.625rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontFamily: 'inherit', fontSize: '0.875rem', resize: 'vertical' }}
            />
          </div>
          <div className="full">
            <GerenciadorCampos campos={camposConfig} onChange={setCamposConfig} />
          </div>
          <label className="full">
            <span>Imagem de Capa (opcional)</span>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setHeroImageFile(e.target.files?.[0] || null)}
            />
          </label>
          <label className="checkbox">
            <input name="ativo" type="checkbox" defaultChecked />
            <span>Formulário ativo</span>
          </label>
          <button type="submit" disabled={criarFormulario.isPending}>
            {criarFormulario.isPending ? 'Criando...' : 'Criar formulário'}
          </button>
        </form>
      </section>

      <section>
        <div className="consultas-admin__section-header">
          <h2>Formulários criados</h2>
          <p>Gerencie os formulários e visualize as inscrições recebidas.</p>
        </div>
        {formularios && formularios.length > 0 ? (
          <div className="consultas-admin__grid">
            {formularios.map((f) => (
              <article key={f.id} className="consultas-admin__card">
                <header>
                  <div>
                    <h3>{f.titulo}</h3>
                    <p>{f.subtitulo || f.descricao || 'Sem descrição.'}</p>
                  </div>
                  <span className={`status-pill ${f.ativo ? 'on' : 'off'}`}>
                    {f.ativo ? 'Ativo' : 'Inativo'}
                  </span>
                </header>
                <dl className="consultas-admin__meta">
                  <div>
                    <dt>Inscrições</dt>
                    <dd>{f.total_inscricoes}</dd>
                  </div>
                  <div>
                    <dt>Criado em</dt>
                    <dd>{new Date(f.created_at).toLocaleDateString('pt-BR')}</dd>
                  </div>
                </dl>
                <div className="consultas-admin__public-link">
                  <div>
                    <small>Link público</small>
                    <a href={f.public_url} target="_blank" rel="noreferrer">
                      {f.public_url}
                    </a>
                  </div>
                  <button type="button" className="ghost" onClick={() => handleCopyLink(f)}>
                    Copiar
                  </button>
                </div>
                <div className="consultas-admin__actions">
                  <button type="button" className="ghost" onClick={() => abrirEdicao(f)}>Editar</button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => setAbaInscricoes((prev) => (prev === f.id ? null : f.id))}
                  >
                    {abaInscricoes === f.id ? 'Fechar inscrições' : 'Ver inscrições'}
                  </button>
                  <button type="button" className="danger" onClick={() => handleDelete(f)}>Excluir</button>
                </div>

                {abaInscricoes === f.id && (
                  <div className="consultas-admin__manifestacoes">
                    <div className="inscricoes-filtro">
                      <input
                        type="text"
                        value={nomeFiltro}
                        onChange={(e) => setNomeFiltro(e.target.value)}
                        placeholder="Filtrar por nome completo..."
                        onKeyDown={(e) => { if (e.key === 'Enter') setNomeFiltroAplicado(nomeFiltro); }}
                        style={{ flex: 1, padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontSize: '0.875rem' }}
                      />
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => setNomeFiltroAplicado(nomeFiltro)}
                        style={{ padding: '0.5rem 1rem', borderRadius: '20px', border: '1px solid var(--color-border)', background: 'var(--color-surface)', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600 }}
                      >
                        Filtrar
                      </button>
                      {inscricoes && inscricoes.length > 0 && (
                        <>
                          <button
                            type="button"
                            className="ghost"
                            onClick={() => exportarCsv(inscricoes, `inscricoes-${f.token_acesso}.csv`)}
                            style={{ padding: '0.5rem 1rem', borderRadius: '20px', border: '1px solid var(--color-primary)', color: 'var(--color-primary)', background: 'var(--color-primary-light)', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600 }}
                          >
                            Exportar CSV
                          </button>
                          <button
                            type="button"
                            className="ghost"
                            onClick={() => exportarPdf(inscricoes, f.titulo)}
                            style={{ padding: '0.5rem 1rem', borderRadius: '20px', border: '1px solid #243b53', color: '#243b53', background: '#f0f4f8', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 600 }}
                          >
                            Exportar PDF
                          </button>
                        </>
                      )}
                    </div>
                    {carregandoInscricoes && <p>Carregando inscrições...</p>}
                    {!carregandoInscricoes && inscricoes && inscricoes.length === 0 && (
                      <p className="muted">Nenhuma inscrição encontrada.</p>
                    )}
                    {!carregandoInscricoes && inscricoes && inscricoes.map((insc) => (
                      <div key={insc.id} className="manifestacao">
                        <div className="manifestacao__header">
                          <span>#{insc.id}</span>
                          <span>{new Date(insc.created_at).toLocaleString('pt-BR')}</span>
                        </div>
                        <p><strong>{insc.nome_completo}</strong>{insc.instituicao_comunidade ? ` — ${insc.instituicao_comunidade}` : ''}</p>
                        {(insc.telefone || insc.email) && (
                          <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                            {insc.telefone && <span>Tel: {insc.telefone} </span>}
                            {insc.email && <span>E-mail: {insc.email}</span>}
                          </p>
                        )}
                        {insc.areas_atuacao && insc.areas_atuacao.length > 0 && (
                          <div className="manifestacao__votos">
                            {insc.areas_atuacao.map((a) => <span key={a} className="manifestacao__voto">{a}</span>)}
                          </div>
                        )}
                        {insc.representacoes && insc.representacoes.length > 0 && (
                          <div className="manifestacao__votos" style={{ marginTop: '4px' }}>
                            {insc.representacoes.map((r) => <span key={r} className="manifestacao__voto" style={{ background: '#f0fdf4', color: '#15803d' }}>{r}</span>)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="consultas-admin__empty">
            <p>Nenhum formulário criado ainda.</p>
          </div>
        )}
      </section>

      {editando && (
        <div className="consultas-admin__modal-overlay">
          <div className="consultas-admin__modal">
            <header className="consultas-admin__modal-header">
              <h3>Editar Formulário de Inscrição</h3>
              <button type="button" className="consultas-admin__modal-close" onClick={() => setEditando(null)}>Fechar</button>
            </header>
            <div className="consultas-admin__modal-body">
              {erro && <span className="consultas-admin__badge danger">{erro}</span>}
              <form className="consultas-admin__form" onSubmit={handleEditar}>
                <label>
                  <span>Título do evento</span>
                  <input name="titulo" type="text" defaultValue={editando.titulo} required />
                </label>
                <label>
                  <span>Subtítulo</span>
                  <input name="subtitulo" type="text" defaultValue={editando.subtitulo} />
                </label>
                <label className="full">
                  <span>Descrição</span>
                  <textarea name="descricao" rows={2} defaultValue={editando.descricao} />
                </label>
                <div className="full consultas-admin__perguntas-section">
                  <div className="consultas-admin__perguntas-header">
                    <span>Opções de Área de Atuação (uma por linha)</span>
                  </div>
                  <textarea
                    rows={6}
                    value={areasTexto}
                    onChange={(e) => setAreasTexto(e.target.value)}
                    style={{ width: '100%', padding: '0.625rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontFamily: 'inherit', fontSize: '0.875rem', resize: 'vertical' }}
                  />
                </div>
                <div className="full consultas-admin__perguntas-section">
                  <div className="consultas-admin__perguntas-header">
                    <span>Opções de Representação (uma por linha)</span>
                  </div>
                  <textarea
                    rows={10}
                    value={repsTexto}
                    onChange={(e) => setRepsTexto(e.target.value)}
                    style={{ width: '100%', padding: '0.625rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontFamily: 'inherit', fontSize: '0.875rem', resize: 'vertical' }}
                  />
                </div>
                <div className="full">
                  <GerenciadorCampos campos={camposConfigEdicao} onChange={setCamposConfigEdicao} />
                </div>
                <label className="full">
                  <span>Imagem de Capa (opcional)</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setHeroImageFile(e.target.files?.[0] || null)}
                  />
                  {editando.imagem_hero_url && (
                    <small style={{ display: 'block', marginTop: '0.25rem' }}>
                      <a href={editando.imagem_hero_url} target="_blank" rel="noreferrer">
                        Visualizar imagem de hero atual
                      </a>
                    </small>
                  )}
                </label>
                <label className="checkbox">
                  <input name="ativo" type="checkbox" defaultChecked={editando.ativo} />
                  <span>Formulário ativo</span>
                </label>
                <button type="submit" disabled={editarFormulario.isPending}>
                  {editarFormulario.isPending ? 'Salvando...' : 'Salvar alterações'}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function ConsultasPublicasPage() {
  const [abaAtiva, setAbaAtiva] = useState<'consultas' | 'inscricoes'>('consultas');

  const CONSULTAS_POR_PAGINA = 12;
  const {
    data: consultas,
    isLoading,
    error: consultasError,
    refetch: refetchConsultas,
  } = useConsultasPublicas();
  const criarConsulta = useCriarConsultaPublica();
  const excluirConsulta = useExcluirConsultaPublica();
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [heroImageFile, setHeroImageFile] = useState<File | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [consultaSelecionada, setConsultaSelecionada] = useState<number | null>(null);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [perguntas, setPerguntas] = useState<PerguntaFormItem[]>([]);
  const { data: manifestacoes, isLoading: carregandoManifestacoes } = useManifestacoesConsulta(consultaSelecionada ?? undefined);
  const totalConsultas = consultas?.length ?? 0;
  const totalPaginas = Math.max(1, Math.ceil(totalConsultas / CONSULTAS_POR_PAGINA));
  const inicioPagina = totalConsultas === 0 ? 0 : (paginaAtual - 1) * CONSULTAS_POR_PAGINA + 1;
  const fimPagina = Math.min(paginaAtual * CONSULTAS_POR_PAGINA, totalConsultas);

  const consultasPaginadas = useMemo(() => {
    if (!consultas || consultas.length === 0) {
      return [];
    }
    const start = (paginaAtual - 1) * CONSULTAS_POR_PAGINA;
    return consultas.slice(start, start + CONSULTAS_POR_PAGINA);
  }, [consultas, paginaAtual]);

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
        imagem_hero: heroImageFile || undefined,
        data_publicacao,
        data_validade,
        data_fechamento,
        perguntas_votacao: perguntas_votacao.length > 0 ? perguntas_votacao : undefined,
        ativa,
      });
      setMensagem('Consulta criada com sucesso! Compartilhe o link público para iniciar a participação.');
      setPerguntas([]);
      setPdfFile(null);
      setHeroImageFile(null);
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

  const editarConsulta = useEditarConsultaPublica();
  const [editingConsulta, setEditingConsulta] = useState<ConsultaPublica | null>(null);

  useEffect(() => {
    if (editingConsulta) {
      setPerguntas(
        editingConsulta.perguntas_votacao?.map((p) => ({
          pergunta: p.pergunta,
          opcoesTexto: p.opcoes.join('\n'),
        })) ?? []
      );
    } else {
      setPerguntas([]);
    }
  }, [editingConsulta]);

  useEffect(() => {
    setPaginaAtual((prev) => Math.min(prev, totalPaginas));
  }, [totalPaginas]);

  const handleEditSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingConsulta) return;

    const formElement = event.currentTarget;
    setMensagem(null);
    setErro(null);

    const form = new FormData(formElement);
    const titulo = String(form.get('titulo') ?? '').trim();
    const slug = String(form.get('slug') ?? '').trim();
    const descricao = String(form.get('descricao') ?? '').trim();
    const data_publicacao = String(form.get('data_publicacao') ?? '').trim();
    const data_validade = String(form.get('data_validade') ?? '').trim() || undefined;
    const data_fechamento = String(form.get('data_fechamento') ?? '').trim() || undefined;
    const ativa = form.get('ativa') !== null;

    const pdfInput = formElement.querySelector('input[name="pdf"]') as HTMLInputElement;
    const newPdfFile = pdfInput?.files?.[0];

    const heroInput = formElement.querySelector('input[name="imagem_hero"]') as HTMLInputElement;
    const newHeroFile = heroInput?.files?.[0];

    if (newPdfFile) {
      if (!newPdfFile.type.toLowerCase().includes('pdf') && !newPdfFile.name.toLowerCase().endsWith('.pdf')) {
        setErro('Envie um arquivo PDF válido (extensão .pdf).');
        return;
      }
      if (newPdfFile.size === 0) {
        setErro('O PDF parece estar vazio.');
        return;
      }
    }

    if (!titulo || !data_publicacao) {
      setErro('Preencha título e data de publicação.');
      return;
    }

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
      await editarConsulta.mutateAsync({
        id: editingConsulta.id,
        titulo,
        slug: slug || undefined,
        descricao: descricao || undefined,
        pdf: newPdfFile || undefined,
        imagem_hero: newHeroFile || undefined,
        data_publicacao,
        data_validade,
        data_fechamento,
        perguntas_votacao: perguntas_votacao.length > 0 ? perguntas_votacao : undefined,
        ativa,
      });
      setMensagem('Consulta atualizada com sucesso!');
      setEditingConsulta(null);
      setPdfFile(null);
      setHeroImageFile(null);
    } catch (error: any) {
      setErro(error?.message ?? 'Não foi possível atualizar a consulta.');
    }
  };

  if (isLoading && !consultas && abaAtiva === 'consultas') {
    return <FullPageLoader message="Carregando consultas públicas..." />;
  }

  return (
    <div className="consultas-admin">
      <header className="consultas-admin__header">
        <div>
          <h1>Consulta pública</h1>
          <p>Publique documentos em PDF para manifestações ou crie formulários de inscrição para audiências públicas.</p>
        </div>
      </header>

      <div className="consultas-admin__tabs">
        <button
          type="button"
          className={`consultas-admin__tab ${abaAtiva === 'consultas' ? 'active' : ''}`}
          onClick={() => setAbaAtiva('consultas')}
        >
          Consultas Públicas
        </button>
        <button
          type="button"
          className={`consultas-admin__tab ${abaAtiva === 'inscricoes' ? 'active' : ''}`}
          onClick={() => setAbaAtiva('inscricoes')}
        >
          Formulários de Inscrição
        </button>
      </div>

      {abaAtiva === 'inscricoes' && <FormulariosInscricaoTab />}

      {abaAtiva === 'consultas' && <>
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
            {mensagem && !editingConsulta && <span className="consultas-admin__badge success">{mensagem}</span>}
            {erro && !editingConsulta && <span className="consultas-admin__badge danger">{erro}</span>}
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
              <span>Imagem de Capa (opcional)</span>
              <input
                name="imagem_hero"
                type="file"
                accept="image/*"
                onChange={(event) => setHeroImageFile(event.target.files?.[0] ?? null)}
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
              {!editingConsulta && perguntas.map((p, index) => (
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
              {!editingConsulta && perguntas.length === 0 && (
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
            <>
              <div className="consultas-admin__pagination">
                <p className="consultas-admin__pagination-info">
                  Mostrando {inicioPagina}-{fimPagina} de {totalConsultas} consultas.
                </p>
                <div className="consultas-admin__pagination-controls">
                  <button
                    type="button"
                    className="ghost"
                    disabled={paginaAtual <= 1}
                    onClick={() => setPaginaAtual((prev) => Math.max(1, prev - 1))}
                  >
                    Anterior
                  </button>
                  <span>
                    Página {paginaAtual} de {totalPaginas}
                  </span>
                  <button
                    type="button"
                    className="ghost"
                    disabled={paginaAtual >= totalPaginas}
                    onClick={() => setPaginaAtual((prev) => Math.min(totalPaginas, prev + 1))}
                  >
                    Próxima
                  </button>
                </div>
              </div>
              <div className="consultas-admin__grid">
                {consultasPaginadas.map((consulta) => (
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
                        <dd>{formatDate(consulta.data_publicacao)}</dd>
                      </div>
                      <div>
                        <dt>Validade</dt>
                        <dd>{formatDate(consulta.data_validade)}</dd>
                      </div>
                      <div>
                        <dt>Encerramento</dt>
                        <dd>{formatDate(consulta.data_fechamento)}</dd>
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
                      <button type="button" className="ghost" onClick={() => setEditingConsulta(consulta)}>
                        Editar
                      </button>
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
            </>
          ) : (
            <div className="consultas-admin__empty">
              <p>Nenhuma consulta publicada ainda.</p>
            </div>
          )}
        </section>

        {editingConsulta && (
          <div className="consultas-admin__modal-overlay">
            <div className="consultas-admin__modal">
              <header className="consultas-admin__modal-header">
                <h3>Editar Consulta Pública</h3>
                <button
                  type="button"
                  className="consultas-admin__modal-close"
                  onClick={() => setEditingConsulta(null)}
                >
                  Fechar
                </button>
              </header>
              <div className="consultas-admin__modal-body">
                {erro && editingConsulta && <span className="consultas-admin__badge danger">{erro}</span>}
                <form className="consultas-admin__form" onSubmit={handleEditSubmit}>
                  <label>
                    <span>Título</span>
                    <input
                      name="titulo"
                      type="text"
                      defaultValue={editingConsulta.titulo}
                      required
                    />
                  </label>
                  <label>
                    <span>Slug (opcional)</span>
                    <input
                      name="slug"
                      type="text"
                      defaultValue={editingConsulta.slug || ''}
                    />
                  </label>
                  <label className="full">
                    <span>Descrição curta (opcional)</span>
                    <textarea
                      name="descricao"
                      rows={3}
                      defaultValue={editingConsulta.descricao || ''}
                    />
                  </label>
                  <label>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Subir novo PDF (opcional)</span>
                      {editingConsulta.pdf_url && (
                        <a href={editingConsulta.pdf_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--color-primary)' }}>
                          Ver PDF Atual
                        </a>
                      )}
                    </div>
                    <input
                      name="pdf"
                      type="file"
                      accept="application/pdf"
                    />
                  </label>
                  <label>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Imagem de Capa (opcional)</span>
                      {editingConsulta.imagem_hero_url && (
                        <a href={editingConsulta.imagem_hero_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--color-primary)' }}>
                          Ver Imagem Atual
                        </a>
                      )}
                    </div>
                    <input
                      name="imagem_hero"
                      type="file"
                      accept="image/*"
                    />
                  </label>
                  <label>
                    <span>Data de publicação</span>
                    <input
                      name="data_publicacao"
                      type="date"
                      required
                      defaultValue={editingConsulta.data_publicacao}
                    />
                  </label>
                  <label>
                    <span>Validade da consulta (opcional)</span>
                    <input
                      name="data_validade"
                      type="date"
                      defaultValue={editingConsulta.data_validade || ''}
                    />
                  </label>
                  <label>
                    <span>Fechamento (opcional)</span>
                    <input
                      name="data_fechamento"
                      type="date"
                      defaultValue={editingConsulta.data_fechamento || ''}
                    />
                  </label>

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
                        Nenhuma pergunta adicionada.
                      </p>
                    )}
                  </div>

                  <label className="checkbox">
                    <input
                      name="ativa"
                      type="checkbox"
                      defaultChecked={editingConsulta.ativa}
                    />
                    <span>Consulta ativa</span>
                  </label>
                  <button type="submit" disabled={editarConsulta.isPending}>
                    {editarConsulta.isPending ? 'Salvando...' : 'Salvar alterações'}
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}
      </>}
    </div>
  );
}
