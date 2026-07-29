from django import forms

from ava.models import AtividadeTentativa, Curso, DocumentoAcompanhamento
from core.models import Cliente, Usuario
from curriculum.models import Escola


class AtividadeTentativaCorrecaoForm(forms.ModelForm):
    class Meta:
        model = AtividadeTentativa
        fields = ["status", "nota_obtida", "feedback_tutor"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "nota_obtida": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "feedback_tutor": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Registre a devolutiva para o aluno.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        atividade = getattr(self.instance, "atividade", None)
        if atividade is not None:
            self.fields["nota_obtida"].help_text = f"Nota máxima da atividade: {atividade.nota_maxima}."


class DocumentoAcompanhamentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoAcompanhamento
        fields = [
            "escola",
            "curso",
            "aluno",
            "categoria",
            "titulo",
            "descricao",
            "periodo_referencia",
            "arquivo",
        ]
        widgets = {
            "escola": forms.Select(attrs={"class": "form-select"}),
            "curso": forms.Select(attrs={"class": "form-select"}),
            "aluno": forms.Select(attrs={"class": "form-select"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Identifique o documento"}
            ),
            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Contexto ou observações importantes (opcional)",
                }
            ),
            "periodo_referencia": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "arquivo": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.doc,.docx,.odt,.xls,.xlsx,.ods,.csv,.jpg,.jpeg,.png",
                }
            ),
        }

    def __init__(self, *args, user, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.cliente = cliente
        escolas = Escola.raw_objects.filter(
            cliente=cliente,
            is_deleted=False,
        ).order_by("nome")
        cursos = Curso.raw_objects.filter(
            cliente=cliente,
            is_deleted=False,
        ).order_by("titulo")
        alunos = (
            Usuario.objects.filter(
                cliente=cliente,
                cursos_matriculados__is_deleted=False,
            )
            .select_related("escola")
            .distinct()
            .order_by("nome", "email")
        )

        if user.role == Usuario.Role.PROFESSOR:
            escolas = escolas.filter(pk=user.escola_id)
            cursos = cursos.filter(
                matriculas__aluno__escola_id=user.escola_id,
                matriculas__is_deleted=False,
            ).distinct()
            alunos = alunos.filter(escola_id=user.escola_id)
            self.fields["escola"].disabled = True
            self.fields["escola"].initial = user.escola_id

        self.fields["escola"].queryset = escolas
        self.fields["curso"].queryset = cursos
        self.fields["aluno"].queryset = alunos
        self.fields["curso"].required = False
        self.fields["aluno"].required = False
        self.fields["curso"].empty_label = "Documento geral da escola"
        self.fields["aluno"].empty_label = "Sem vínculo com aluno específico"
        self.fields["arquivo"].help_text = (
            "PDF, documentos, planilhas ou imagens. Tamanho máximo: 20 MB."
        )
        if self.instance and self.instance.pk:
            self.fields["arquivo"].required = False
            self.fields["arquivo"].help_text += " Deixe vazio para manter o arquivo atual."

    def clean(self):
        cleaned_data = super().clean()
        escola = cleaned_data.get("escola")
        curso = cleaned_data.get("curso")
        aluno = cleaned_data.get("aluno")
        if escola and escola.cliente_id != self.cliente.id:
            self.add_error("escola", "Selecione uma escola do município atual.")
        if curso and curso.cliente_id != self.cliente.id:
            self.add_error("curso", "Selecione uma turma/curso do município atual.")
        if aluno:
            if aluno.cliente_id != self.cliente.id:
                self.add_error("aluno", "Selecione um aluno do município atual.")
            elif escola and aluno.escola_id != escola.id:
                self.add_error("aluno", "O aluno deve pertencer à escola selecionada.")
            elif curso and not curso.matriculas.filter(
                aluno=aluno,
                is_deleted=False,
            ).exists():
                self.add_error("aluno", "O aluno não está matriculado na turma/curso selecionada.")
        return cleaned_data


class CursoEstruturaCopyForm(forms.Form):
    curso_origem = forms.ModelChoiceField(
        label="Curso de origem",
        queryset=Curso.raw_objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cliente_destino = forms.ModelChoiceField(
        label="Município destino",
        queryset=Cliente.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    novo_titulo = forms.CharField(
        label="Novo título",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Se vazio, usa o título original.",
            }
        ),
        help_text="Opcional. Use para diferenciar o curso no município destino.",
    )
    novo_slug = forms.SlugField(
        label="Novo slug",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Gerado automaticamente se ficar vazio.",
            }
        ),
        help_text="Opcional. Se vazio, o sistema gera um slug único automaticamente.",
    )
    copiar_atividades = forms.BooleanField(
        label="Copiar também atividades avaliativas",
        required=False,
        initial=False,
        help_text="Desmarcado por padrão: copia curso, módulos, aulas e conteúdos, sem quizzes/tarefas/fórum.",
    )
    manter_status_publicacao = forms.BooleanField(
        label="Manter status do curso original",
        required=False,
        initial=False,
        help_text="Se desmarcado, o curso copiado nasce como rascunho no destino.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso_origem"].queryset = (
            Curso.raw_objects.select_related("cliente").order_by("cliente__nome", "titulo")
        )
        self.fields["cliente_destino"].queryset = Cliente.objects.filter(ativo=True).order_by("nome")
        self.fields["curso_origem"].label_from_instance = (
            lambda curso: f"{curso.titulo} ({getattr(curso.cliente, 'nome', 'Sem cliente')})"
        )


class AtividadeForumMensagemForm(forms.Form):
    mensagem = forms.CharField(
        label="Mensagem",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Compartilhe sua contribuição com a turma.",
            }
        ),
    )
    resposta_para = forms.IntegerField(required=False, widget=forms.HiddenInput())

    def clean_mensagem(self):
        return (self.cleaned_data.get("mensagem") or "").strip()
