"""Formulários das salas de GT do Referencial."""

from __future__ import annotations

import csv
import io
import json

from django import forms

from ava.models.gt_sala import (
    AtaReuniaoGT,
    CicloReferencial,
    EstrategiaGT,
    InscricaoSalaGT,
    MetaGT,
    ObjetivoReferencial,
    ReuniaoGT,
    SalaGT,
    TrabalhoGT,
)
from core.models import Usuario
from curriculum.models import GT


TEXTAREA = {"class": "form-control", "rows": 4}
TEXTAREA_CURTA = {"class": "form-control", "rows": 2}
INPUT = {"class": "form-control"}
SELECT = {"class": "form-select"}
CHECK = {"class": "form-check-input"}
DATA = {"class": "form-control", "type": "date"}


class CicloReferencialForm(forms.ModelForm):
    class Meta:
        model = CicloReferencial
        fields = [
            "nome",
            "descricao",
            "inicio",
            "fim",
            "ativo",
            "inscricoes_abertas",
            "inscricoes_inicio",
            "inscricoes_fim",
            "confirmacao_automatica",
            "max_salas_por_participante",
            "permite_lista_espera",
            "min_metas_para_aprovacao",
            "min_estrategias_para_aprovacao",
            "exige_ata_para_aprovacao",
        ]
        widgets = {
            "nome": forms.TextInput(attrs=INPUT),
            "descricao": forms.Textarea(attrs=TEXTAREA_CURTA),
            "inicio": forms.DateInput(attrs=DATA, format="%Y-%m-%d"),
            "fim": forms.DateInput(attrs=DATA, format="%Y-%m-%d"),
            "inscricoes_inicio": forms.DateInput(attrs=DATA, format="%Y-%m-%d"),
            "inscricoes_fim": forms.DateInput(attrs=DATA, format="%Y-%m-%d"),
            "ativo": forms.CheckboxInput(attrs=CHECK),
            "inscricoes_abertas": forms.CheckboxInput(attrs=CHECK),
            "confirmacao_automatica": forms.CheckboxInput(attrs=CHECK),
            "permite_lista_espera": forms.CheckboxInput(attrs=CHECK),
            "exige_ata_para_aprovacao": forms.CheckboxInput(attrs=CHECK),
            "max_salas_por_participante": forms.NumberInput(attrs={**INPUT, "min": "1"}),
            "min_metas_para_aprovacao": forms.NumberInput(attrs={**INPUT, "min": "0"}),
            "min_estrategias_para_aprovacao": forms.NumberInput(attrs={**INPUT, "min": "0"}),
        }


class ObjetivoReferencialForm(forms.ModelForm):
    class Meta:
        model = ObjetivoReferencial
        fields = ["codigo", "ordem", "titulo", "texto", "ativo"]
        widgets = {
            "codigo": forms.TextInput(attrs={**INPUT, "placeholder": "01"}),
            "ordem": forms.NumberInput(attrs={**INPUT, "min": "0"}),
            "titulo": forms.TextInput(attrs=INPUT),
            "texto": forms.Textarea(attrs={**TEXTAREA, "rows": 6}),
            "ativo": forms.CheckboxInput(attrs=CHECK),
        }


class ImportacaoObjetivosForm(forms.Form):
    """Importa os objetivos oficiais sem fixar nada em código.

    Aceita CSV (``codigo;titulo;texto``) ou JSON — colado na tela ou enviado
    como arquivo. O ``codigo`` é a chave estável: reimportar atualiza o texto
    sem criar duplicata.
    """

    arquivo = forms.FileField(
        label="Arquivo CSV ou JSON",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv,.json,.txt"}),
    )
    conteudo = forms.CharField(
        label="Ou cole o conteúdo aqui",
        required=False,
        widget=forms.Textarea(
            attrs={
                **TEXTAREA,
                "rows": 8,
                "placeholder": "codigo;titulo;texto\n01;Objetivo 1;Redação oficial do objetivo 1",
            }
        ),
    )
    desativar_ausentes = forms.BooleanField(
        label="Desativar objetivos que não estiverem no arquivo",
        required=False,
        widget=forms.CheckboxInput(attrs=CHECK),
        help_text="Nenhum registro é apagado: os ausentes apenas deixam de ficar ativos.",
    )

    def clean(self):
        dados = super().clean()
        arquivo = dados.get("arquivo")
        conteudo = (dados.get("conteudo") or "").strip()
        if not arquivo and not conteudo:
            raise forms.ValidationError("Envie um arquivo ou cole o conteúdo dos objetivos.")
        if arquivo:
            if arquivo.size > 2 * 1024 * 1024:
                raise forms.ValidationError({"arquivo": "O arquivo deve ter no máximo 2 MB."})
            bruto = arquivo.read()
            try:
                conteudo = bruto.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    conteudo = bruto.decode("latin-1")
                except UnicodeDecodeError as exc:  # pragma: no cover - entrada inválida
                    raise forms.ValidationError(
                        {"arquivo": "Não foi possível ler o arquivo enviado."}
                    ) from exc
        dados["registros"] = self._extrair(conteudo)
        return dados

    @staticmethod
    def _extrair(conteudo: str) -> list[dict]:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            return []
        if conteudo[0] in "[{":
            try:
                carga = json.loads(conteudo)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(f"JSON inválido: {exc.msg}.") from exc
            if isinstance(carga, dict):
                carga = carga.get("objetivos") or []
            registros = []
            for item in carga:
                if not isinstance(item, dict):
                    continue
                registros.append(
                    {
                        "codigo": str(item.get("codigo", "")).strip(),
                        "titulo": str(item.get("titulo", "")).strip(),
                        "texto": str(item.get("texto", "")).strip(),
                        "ordem": item.get("ordem"),
                    }
                )
        else:
            amostra = conteudo[:1000]
            try:
                dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t")
            except csv.Error:
                dialeto = csv.excel
                dialeto.delimiter = ";"
            leitor = csv.reader(io.StringIO(conteudo), dialeto)
            registros = []
            for indice, linha in enumerate(leitor):
                if not linha or not any(campo.strip() for campo in linha):
                    continue
                primeiro = linha[0].strip().lower()
                if indice == 0 and primeiro in {"codigo", "código", "code"}:
                    continue
                registros.append(
                    {
                        "codigo": linha[0].strip(),
                        "titulo": linha[1].strip() if len(linha) > 1 else "",
                        "texto": linha[2].strip() if len(linha) > 2 else "",
                        "ordem": linha[3].strip() if len(linha) > 3 else None,
                    }
                )

        validos = []
        for posicao, registro in enumerate(registros, start=1):
            if not registro["codigo"]:
                raise forms.ValidationError(
                    f"Linha {posicao}: informe o código do objetivo."
                )
            if not registro["titulo"]:
                raise forms.ValidationError(
                    f"Linha {posicao} ({registro['codigo']}): informe o título do objetivo."
                )
            try:
                registro["ordem"] = (
                    int(registro["ordem"]) if registro["ordem"] not in (None, "") else posicao
                )
            except (TypeError, ValueError):
                registro["ordem"] = posicao
            validos.append(registro)
        if not validos:
            raise forms.ValidationError("Nenhum objetivo foi reconhecido no conteúdo informado.")
        return validos


class SalaGTForm(forms.ModelForm):
    class Meta:
        model = SalaGT
        fields = [
            "ciclo",
            "objetivo",
            "gt",
            "capacidade",
            "inscricoes_abertas",
            "inscricoes_inicio",
            "inscricoes_fim",
            "permite_lista_espera",
            "participantes_editam_conteudo",
            "situacao",
            "observacoes",
        ]
        widgets = {
            "ciclo": forms.Select(attrs=SELECT),
            "objetivo": forms.Select(attrs=SELECT),
            "gt": forms.Select(attrs=SELECT),
            "capacidade": forms.NumberInput(attrs={**INPUT, "min": "1"}),
            "inscricoes_abertas": forms.CheckboxInput(attrs=CHECK),
            "inscricoes_inicio": forms.DateInput(attrs=DATA, format="%Y-%m-%d"),
            "inscricoes_fim": forms.DateInput(attrs=DATA, format="%Y-%m-%d"),
            "permite_lista_espera": forms.CheckboxInput(attrs=CHECK),
            "participantes_editam_conteudo": forms.CheckboxInput(attrs=CHECK),
            "situacao": forms.Select(attrs=SELECT),
            "observacoes": forms.Textarea(attrs=TEXTAREA_CURTA),
        }

    def __init__(self, *args, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ciclo"].queryset = CicloReferencial.raw_objects.filter(
            is_deleted=False, cliente=cliente
        ).order_by("-inicio", "nome")
        self.fields["objetivo"].queryset = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente=cliente
        ).order_by("ordem", "codigo")
        self.fields["gt"].queryset = GT.raw_objects.filter(
            is_deleted=False, cliente=cliente
        ).order_by("nome")


class GerarSalasForm(forms.Form):
    capacidade = forms.IntegerField(
        label="Limite de participantes por sala",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={**INPUT, "min": "1"}),
        help_text="Deixe vazio para criar as salas sem limite de vagas.",
    )
    criar_gt_ausente = forms.BooleanField(
        label="Criar o GT quando ainda não existir",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs=CHECK),
        help_text="O GT é criado no cadastro do Referencial (não há cadastro paralelo no AVA).",
    )


class DiagnosticoGTForm(forms.ModelForm):
    class Meta:
        model = TrabalhoGT
        fields = [
            "diagnostico_nao_aplicavel",
            "diagnostico_situacao",
            "diagnostico_evidencias",
            "diagnostico_desafios",
            "diagnostico_potencialidades",
            "diagnostico_publico",
        ]
        widgets = {
            "diagnostico_nao_aplicavel": forms.CheckboxInput(attrs=CHECK),
            "diagnostico_situacao": forms.Textarea(attrs={**TEXTAREA, "rows": 6}),
            "diagnostico_evidencias": forms.Textarea(attrs=TEXTAREA),
            "diagnostico_desafios": forms.Textarea(attrs=TEXTAREA),
            "diagnostico_potencialidades": forms.Textarea(attrs=TEXTAREA),
            "diagnostico_publico": forms.Textarea(attrs=TEXTAREA_CURTA),
        }
        help_texts = {
            "diagnostico_situacao": (
                "Use uma linha por item e inicie com “- ” para gerar uma lista no documento."
            ),
        }

    def clean(self):
        dados = super().clean()
        if not dados.get("diagnostico_nao_aplicavel") and not (
            dados.get("diagnostico_situacao") or ""
        ).strip():
            self.add_error(
                "diagnostico_situacao",
                "Descreva a situação atual ou marque que o diagnóstico não se aplica.",
            )
        return dados


class QuadroObjetivoGTForm(forms.ModelForm):
    class Meta:
        model = TrabalhoGT
        fields = ["objetivo_proposto", "observacoes", "pendencias"]
        widgets = {
            "objetivo_proposto": forms.Textarea(attrs={**TEXTAREA, "rows": 5}),
            "observacoes": forms.Textarea(attrs=TEXTAREA_CURTA),
            "pendencias": forms.Textarea(attrs=TEXTAREA_CURTA),
        }


class MetaGTForm(forms.ModelForm):
    class Meta:
        model = MetaGT
        fields = ["ordem", "descricao", "indicador", "prazo", "observacoes"]
        widgets = {
            "ordem": forms.NumberInput(attrs={**INPUT, "min": "1"}),
            "descricao": forms.Textarea(attrs=TEXTAREA_CURTA),
            "indicador": forms.Textarea(attrs=TEXTAREA_CURTA),
            "prazo": forms.TextInput(attrs={**INPUT, "placeholder": "2026 · 1º semestre"}),
            "observacoes": forms.Textarea(attrs=TEXTAREA_CURTA),
        }


class EstrategiaGTForm(forms.ModelForm):
    metas = forms.ModelMultipleChoiceField(
        label="Metas atendidas",
        required=False,
        queryset=MetaGT.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = EstrategiaGT
        fields = ["ordem", "descricao", "responsavel", "prazo", "recursos", "indicador"]
        widgets = {
            "ordem": forms.NumberInput(attrs={**INPUT, "min": "1"}),
            "descricao": forms.Textarea(attrs=TEXTAREA_CURTA),
            "responsavel": forms.TextInput(attrs=INPUT),
            "prazo": forms.TextInput(attrs=INPUT),
            "recursos": forms.Textarea(attrs=TEXTAREA_CURTA),
            "indicador": forms.Textarea(attrs=TEXTAREA_CURTA),
        }

    def __init__(self, *args, trabalho, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["metas"].queryset = MetaGT.raw_objects.filter(
            is_deleted=False, trabalho=trabalho
        ).order_by("ordem", "id")


class ReuniaoGTForm(forms.ModelForm):
    class Meta:
        model = ReuniaoGT
        fields = ["titulo", "data_hora", "modalidade", "local", "link", "pauta", "situacao"]
        widgets = {
            "titulo": forms.TextInput(attrs=INPUT),
            "data_hora": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "modalidade": forms.Select(attrs=SELECT),
            "local": forms.TextInput(attrs=INPUT),
            "link": forms.URLInput(attrs=INPUT),
            "pauta": forms.Textarea(attrs=TEXTAREA),
            "situacao": forms.Select(attrs=SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_hora"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
        ]
        self.fields["local"].required = False
        self.fields["link"].required = False


class AtaGTForm(forms.ModelForm):
    class Meta:
        model = AtaReuniaoGT
        fields = ["pauta", "sintese", "decisoes", "encaminhamentos", "pendencias", "assinaturas"]
        widgets = {
            "pauta": forms.Textarea(attrs=TEXTAREA),
            "sintese": forms.Textarea(attrs={**TEXTAREA, "rows": 8}),
            "decisoes": forms.Textarea(attrs=TEXTAREA),
            "encaminhamentos": forms.Textarea(attrs=TEXTAREA),
            "pendencias": forms.Textarea(attrs=TEXTAREA_CURTA),
            "assinaturas": forms.Textarea(attrs=TEXTAREA_CURTA),
        }
        help_texts = {
            "assinaturas": (
                "Deixe vazio para o documento gerar as linhas de assinatura/ciência "
                "dos participantes."
            ),
        }


class ModeloAtaGTForm(forms.Form):
    nome = forms.CharField(
        label="Nome do modelo",
        max_length=150,
        widget=forms.TextInput(attrs=INPUT),
    )
    cabecalho = forms.CharField(
        label="Cabeçalho institucional",
        required=False,
        widget=forms.Textarea(attrs=TEXTAREA_CURTA),
    )
    rodape = forms.CharField(
        label="Rodapé institucional",
        required=False,
        widget=forms.Textarea(attrs=TEXTAREA_CURTA),
    )
    orientacoes = forms.CharField(
        label="Orientações de preenchimento",
        required=False,
        widget=forms.Textarea(attrs=TEXTAREA_CURTA),
    )
    secoes = forms.CharField(
        label="Seções (uma por linha, no formato chave|título)",
        required=False,
        widget=forms.Textarea(
            attrs={
                **TEXTAREA,
                "rows": 7,
                "placeholder": "pauta|Pauta\nsintese|Síntese das discussões",
            }
        ),
        help_text=(
            "Deixe vazio para usar as seções padrão. Publicar gera uma nova versão: "
            "as atas já geradas não mudam."
        ),
    )

    def clean_secoes(self):
        bruto = (self.cleaned_data.get("secoes") or "").strip()
        if not bruto:
            return None
        secoes = []
        for numero, linha in enumerate(bruto.splitlines(), start=1):
            linha = linha.strip()
            if not linha:
                continue
            if "|" in linha:
                chave, titulo = linha.split("|", 1)
            else:
                chave, titulo = linha, linha
            chave = chave.strip().lower().replace(" ", "_")
            if not chave:
                raise forms.ValidationError(f"Linha {numero}: informe a chave da seção.")
            secoes.append({"chave": chave, "titulo": titulo.strip() or chave, "orientacao": ""})
        return secoes or None


class JustificativaForm(forms.Form):
    """Justificativa obrigatória para reabrir, corrigir ou arquivar."""

    justificativa = forms.CharField(
        label="Justificativa",
        widget=forms.Textarea(attrs={**TEXTAREA_CURTA, "rows": 3}),
        max_length=2000,
    )


class ParecerRevisaoForm(forms.Form):
    parecer = forms.CharField(
        label="Ajustes solicitados",
        widget=forms.Textarea(attrs={**TEXTAREA, "rows": 4}),
        max_length=4000,
    )


class InscricaoManualForm(forms.Form):
    """Inscrição feita pela coordenação/administração."""

    usuario = forms.ModelChoiceField(
        label="Participante",
        queryset=Usuario.objects.none(),
        widget=forms.Select(attrs=SELECT),
    )
    papel = forms.ChoiceField(
        label="Papel na sala",
        choices=InscricaoSalaGT.Papel.choices,
        initial=InscricaoSalaGT.Papel.PARTICIPANTE,
        widget=forms.Select(attrs=SELECT),
    )

    def __init__(self, *args, cliente, excluir_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Usuario.objects.filter(cliente=cliente, is_active=True)
        if excluir_ids:
            queryset = queryset.exclude(pk__in=list(excluir_ids))
        self.fields["usuario"].queryset = queryset.order_by("nome", "email")


class SituacaoSalaForm(forms.Form):
    situacao = forms.ChoiceField(
        label="Nova situação",
        choices=SalaGT.Situacao.choices,
        widget=forms.Select(attrs=SELECT),
    )
    justificativa = forms.CharField(
        label="Justificativa",
        required=False,
        widget=forms.Textarea(attrs={**TEXTAREA_CURTA, "rows": 3}),
        max_length=2000,
        help_text="Obrigatória para concluir ou arquivar a sala.",
    )
