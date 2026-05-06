from django import forms

from ava.models import AtividadeTentativa, Curso
from core.models import Cliente


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
            self.fields["nota_obtida"].help_text = f"Nota maxima da atividade: {atividade.nota_maxima}."


class CursoEstruturaCopyForm(forms.Form):
    curso_origem = forms.ModelChoiceField(
        label="Curso de origem",
        queryset=Curso.raw_objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cliente_destino = forms.ModelChoiceField(
        label="Municipio destino",
        queryset=Cliente.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    novo_titulo = forms.CharField(
        label="Novo titulo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Se vazio, usa o titulo original.",
            }
        ),
        help_text="Opcional. Use para diferenciar o curso no municipio destino.",
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
        help_text="Opcional. Se vazio, o sistema gera um slug unico automaticamente.",
    )
    copiar_atividades = forms.BooleanField(
        label="Copiar tambem atividades avaliativas",
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
                "placeholder": "Compartilhe sua contribuicao com a turma.",
            }
        ),
    )
    resposta_para = forms.IntegerField(required=False, widget=forms.HiddenInput())

    def clean_mensagem(self):
        return (self.cleaned_data.get("mensagem") or "").strip()
