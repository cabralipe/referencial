"""Formulários do Diário de Bordo e das planilhas configuráveis."""

from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from ava.models import (
    Aula,
    ColunaPlanilha,
    Curso,
    CursoModulo,
    DiarioBordo,
    DiarioBordoMidia,
    DiarioBordoParticipante,
    ImportacaoPlanilha,
    ModeloPlanilha,
)
from ava.models.diario import (
    ALLOWED_DIARIO_MIDIA_EXTENSIONS,
    ORIGENS_COM_EXTERNO,
    ORIGENS_COM_SISTEMA,
)
from core.models import Usuario
from curriculum.models import Escola


CAMPOS_DO_SISTEMA = ["curso", "modulo", "aula"]
CAMPOS_EXTERNOS = [
    "tipo_atividade",
    "local_realizacao",
    "instituicao_parceira",
    "grupo_participante",
    "responsavel_externo",
]


class DiarioBordoForm(forms.ModelForm):
    """Formulário único para aulas internas, externas e híbridas.

    Os campos exibidos mudam conforme a origem selecionada; o template usa
    ``data-origem-grupo`` para alternar os blocos sem recarregar a página.
    """

    class Meta:
        model = DiarioBordo
        fields = [
            "origem",
            "escola",
            "professor",
            "curso",
            "modulo",
            "aula",
            "data_aula",
            "titulo",
            "conteudo_trabalhado",
            "metodologia",
            "tipo_atividade",
            "local_realizacao",
            "instituicao_parceira",
            "grupo_participante",
            "responsavel_externo",
            "frequencia_nominal",
            "participantes_previstos",
            "participantes_presentes",
            "observacoes",
        ]
        widgets = {
            "origem": forms.Select(attrs={"class": "form-select", "id": "id_origem"}),
            "escola": forms.Select(attrs={"class": "form-select"}),
            "professor": forms.Select(attrs={"class": "form-select"}),
            "curso": forms.Select(attrs={"class": "form-select"}),
            "modulo": forms.Select(attrs={"class": "form-select"}),
            "aula": forms.Select(attrs={"class": "form-select"}),
            "data_aula": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "titulo": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Assunto do encontro"}
            ),
            "conteudo_trabalhado": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "metodologia": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo_atividade": forms.Select(attrs={"class": "form-select"}),
            "local_realizacao": forms.TextInput(attrs={"class": "form-control"}),
            "instituicao_parceira": forms.TextInput(attrs={"class": "form-control"}),
            "grupo_participante": forms.TextInput(attrs={"class": "form-control"}),
            "responsavel_externo": forms.TextInput(attrs={"class": "form-control"}),
            "frequencia_nominal": forms.CheckboxInput(
                attrs={"class": "form-check-input", "id": "id_frequencia_nominal"}
            ),
            "participantes_previstos": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "participantes_presentes": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, user, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.cliente = cliente

        escolas = Escola.raw_objects.filter(
            cliente=cliente, is_deleted=False
        ).order_by("nome")
        professores = Usuario.objects.filter(
            cliente=cliente,
            role__in=[Usuario.Role.PROFESSOR, Usuario.Role.COORDENADOR_PEDAGOGICO],
        ).order_by("nome", "email")
        cursos = Curso.raw_objects.filter(cliente=cliente, is_deleted=False).order_by(
            "titulo"
        )
        modulos = CursoModulo.raw_objects.filter(
            cliente=cliente, is_deleted=False
        ).select_related("curso").order_by("curso__titulo", "ordem")
        aulas = Aula.raw_objects.filter(
            cliente=cliente, is_deleted=False
        ).select_related("modulo").order_by("modulo__titulo", "ordem")

        if user.role == Usuario.Role.PROFESSOR:
            escolas = escolas.filter(pk=user.escola_id)
            professores = professores.filter(pk=user.pk)
            self.fields["escola"].initial = user.escola_id
            self.fields["professor"].initial = user.pk
            self.fields["escola"].disabled = True
            self.fields["professor"].disabled = True

        self.fields["escola"].queryset = escolas
        self.fields["professor"].queryset = professores
        self.fields["curso"].queryset = cursos
        self.fields["modulo"].queryset = modulos
        self.fields["aula"].queryset = aulas

        for nome in CAMPOS_DO_SISTEMA:
            self.fields[nome].required = False
            self.fields[nome].empty_label = "—"
        for nome in CAMPOS_EXTERNOS:
            self.fields[nome].required = False

        self.fields["curso"].help_text = (
            "Obrigatório quando a origem for 'No sistema' ou 'Híbrida'."
        )
        self.fields["aula"].help_text = (
            "Vincule a uma aula já cadastrada para não duplicar o registro."
        )
        self.fields["participantes_presentes"].help_text = (
            "Calculado automaticamente quando a lista nominal estiver ativa."
        )

        # Marca os grupos para o JS do template alternar a visibilidade.
        for nome in CAMPOS_DO_SISTEMA:
            self.fields[nome].widget.attrs["data-origem-grupo"] = "sistema"
        for nome in CAMPOS_EXTERNOS:
            self.fields[nome].widget.attrs["data-origem-grupo"] = "externo"

    def clean(self):
        cleaned = super().clean()
        origem = cleaned.get("origem")

        # Campos desabilitados não chegam no POST; repõe a partir do usuário.
        if self.user.role == Usuario.Role.PROFESSOR:
            cleaned["escola"] = self.user.escola
            cleaned["professor"] = self.user

        if origem in ORIGENS_COM_SISTEMA and not cleaned.get("curso"):
            self.add_error(
                "curso", "Informe o curso/turma para aulas realizadas no sistema."
            )
        if origem and origem not in ORIGENS_COM_SISTEMA:
            for nome in CAMPOS_DO_SISTEMA:
                cleaned[nome] = None
        if origem in ORIGENS_COM_EXTERNO:
            if not cleaned.get("local_realizacao"):
                self.add_error(
                    "local_realizacao", "Informe o local onde a atividade ocorreu."
                )
            if not cleaned.get("tipo_atividade"):
                self.add_error("tipo_atividade", "Informe o tipo da atividade.")
        elif origem:
            for nome in ("tipo_atividade", "local_realizacao", "instituicao_parceira"):
                cleaned[nome] = ""

        modulo = cleaned.get("modulo")
        curso = cleaned.get("curso")
        aula = cleaned.get("aula")
        if modulo and curso and modulo.curso_id != curso.id:
            self.add_error("modulo", "O módulo deve pertencer ao curso selecionado.")
        if aula and modulo and aula.modulo_id != modulo.id:
            self.add_error("aula", "A aula deve pertencer ao módulo selecionado.")
        if aula and not modulo:
            cleaned["modulo"] = aula.modulo
            if not curso:
                cleaned["curso"] = aula.modulo.curso
        return cleaned


class DiarioBordoMidiaForm(forms.ModelForm):
    class Meta:
        model = DiarioBordoMidia
        fields = ["tipo", "arquivo", "legenda", "consentimento_registrado"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "arquivo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ",".join(
                        f".{ext}" for ext in ALLOWED_DIARIO_MIDIA_EXTENSIONS
                    ),
                }
            ),
            "legenda": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Descreva a imagem"}
            ),
            "consentimento_registrado": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arquivo"].help_text = "Máximo de 10 MB por arquivo."
        self.fields["consentimento_registrado"].help_text = (
            "Marque somente se houver autorização de uso de imagem (LGPD)."
        )


class DiarioBordoParticipanteForm(forms.ModelForm):
    class Meta:
        model = DiarioBordoParticipante
        fields = ["nome", "identificacao", "presente", "justificativa"]
        widgets = {
            "nome": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nome do participante"}
            ),
            "identificacao": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Matrícula/turma"}
            ),
            "presente": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "justificativa": forms.TextInput(attrs={"class": "form-control"}),
        }


class DiarioBordoRevisaoForm(forms.Form):
    parecer = forms.CharField(
        label="Parecer da revisão",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    bloquear = forms.BooleanField(
        label="Bloquear novas edições",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


# ----------------------------------------------------------------------
# Planilha configurável
# ----------------------------------------------------------------------


class ModeloPlanilhaForm(forms.ModelForm):
    class Meta:
        model = ModeloPlanilha
        fields = [
            "nome",
            "slug",
            "descricao",
            "versao",
            "ativo",
            "escola",
            "curso",
            "permite_professor",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Gerado a partir do nome"}
            ),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "versao": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "escola": forms.Select(attrs={"class": "form-select"}),
            "curso": forms.Select(attrs={"class": "form-select"}),
            "permite_professor": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.cliente = cliente
        self.fields["escola"].queryset = Escola.raw_objects.filter(
            cliente=cliente, is_deleted=False
        ).order_by("nome")
        self.fields["curso"].queryset = Curso.raw_objects.filter(
            cliente=cliente, is_deleted=False
        ).order_by("titulo")
        self.fields["escola"].required = False
        self.fields["curso"].required = False
        self.fields["escola"].empty_label = "Todo o município"
        self.fields["curso"].empty_label = "Qualquer curso/turma"
        self.fields["slug"].required = False


class ColunaPlanilhaForm(forms.ModelForm):
    opcoes_texto = forms.CharField(
        label="Opções de seleção",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Uma opção por linha",
            }
        ),
        help_text="Uma opção por linha. Usado apenas no tipo 'Seleção'.",
    )

    class Meta:
        model = ColunaPlanilha
        fields = [
            "titulo",
            "chave",
            "tipo",
            "ordem",
            "obrigatorio",
            "visivel",
            "valor_padrao",
            "ajuda",
            "validacoes",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "chave": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "gerado do título"}
            ),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "ordem": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "obrigatorio": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "visivel": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "valor_padrao": forms.TextInput(attrs={"class": "form-control"}),
            "ajuda": forms.TextInput(attrs={"class": "form-control"}),
            "validacoes": forms.Textarea(
                attrs={
                    "class": "form-control font-monospace",
                    "rows": 2,
                    "placeholder": '{"min": 0, "max": 10}',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chave"].required = False
        self.fields["validacoes"].required = False
        if self.instance and self.instance.pk:
            self.fields["opcoes_texto"].initial = "\n".join(
                self.instance.opcoes_normalizadas()
            )

    def clean_validacoes(self):
        valor = self.cleaned_data.get("validacoes")
        if valor in (None, "", {}):
            return {}
        if isinstance(valor, dict):
            return valor
        raise forms.ValidationError("Informe um objeto JSON válido.")

    def clean(self):
        cleaned = super().clean()
        opcoes = [
            linha.strip()
            for linha in (cleaned.get("opcoes_texto") or "").splitlines()
            if linha.strip()
        ]
        self.instance.opcoes = opcoes
        if cleaned.get("tipo") == ColunaPlanilha.Tipo.SELECAO and not opcoes:
            self.add_error(
                "opcoes_texto", "Informe ao menos uma opção para colunas de seleção."
            )
        return cleaned


ColunaPlanilhaFormSet = inlineformset_factory(
    ModeloPlanilha,
    ColunaPlanilha,
    form=ColunaPlanilhaForm,
    extra=3,
    can_delete=True,
)


class ImportacaoUploadForm(forms.ModelForm):
    class Meta:
        model = ImportacaoPlanilha
        fields = ["arquivo", "modo"]
        widgets = {
            "arquivo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".xlsx,.xlsm,.xls,.csv,.ods"}
            ),
            "modo": forms.RadioSelect(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["modo"].widget = forms.RadioSelect(
            choices=ImportacaoPlanilha.Modo.choices
        )
        self.fields["arquivo"].help_text = (
            "XLSX ou CSV. XLS e ODS dependem das bibliotecas instaladas no servidor. "
            "Máximo de 20 MB."
        )


class MapeamentoImportacaoForm(forms.Form):
    """Casa cada cabeçalho do arquivo com uma coluna configurada."""

    coluna_chave = forms.ChoiceField(
        label="Coluna usada como chave",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, modelo: ModeloPlanilha, cabecalhos: list[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.modelo = modelo
        self.cabecalhos = cabecalhos
        colunas = list(modelo.colunas_ativas())
        escolhas = [("", "Ignorar esta coluna")] + [
            (coluna.chave, f"{coluna.titulo} ({coluna.get_tipo_display()})")
            for coluna in colunas
        ]
        for indice, cabecalho in enumerate(cabecalhos):
            self.fields[f"col_{indice}"] = forms.ChoiceField(
                label=cabecalho,
                choices=escolhas,
                required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
            )
        self.fields["coluna_chave"].choices = [("", "—")] + [
            (coluna.chave, coluna.titulo) for coluna in colunas
        ]

    def campos_de_mapeamento(self):
        for indice, cabecalho in enumerate(self.cabecalhos):
            yield cabecalho, self[f"col_{indice}"]

    def clean(self):
        cleaned = super().clean()
        mapeamento: dict[str, str] = {}
        usadas: set[str] = set()
        for indice, cabecalho in enumerate(self.cabecalhos):
            chave = cleaned.get(f"col_{indice}")
            if not chave:
                continue
            if chave in usadas:
                self.add_error(
                    f"col_{indice}",
                    "Esta coluna já foi mapeada para outro cabeçalho.",
                )
                continue
            usadas.add(chave)
            mapeamento[cabecalho] = chave
        if not mapeamento:
            raise forms.ValidationError(
                "Mapeie ao menos um cabeçalho da planilha para uma coluna configurada."
            )
        cleaned["mapeamento"] = mapeamento
        return cleaned
