"""Campos compartilhados de configuração da frequência."""
from django import forms


class LinkExpirationField(forms.SplitDateTimeField):
    def __init__(self, **kwargs):
        super().__init__(
            label="Data e horário de expiração do link",
            required=False,
            input_date_formats=["%Y-%m-%d"],
            input_time_formats=["%H:%M", "%H:%M:%S"],
            widget=forms.SplitDateTimeWidget(
                date_format="%Y-%m-%d", time_format="%H:%M",
                date_attrs={"type": "date", "class": "form-control", "aria-label": "Data de expiração"},
                time_attrs={"type": "time", "class": "form-control", "aria-label": "Horário de expiração", "step": "60"},
            ),
            help_text="Informe a data e a hora locais. O link será encerrado automaticamente nesse instante.",
            **kwargs,
        )
