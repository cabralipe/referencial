from django import forms

from ava.models import AtividadeTentativa


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
