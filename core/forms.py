"""Formulários customizados para o Django Admin."""

from pathlib import Path
from uuid import uuid4

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.files.storage import default_storage

from .models import ClienteTema, Usuario


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome", "cliente", "role", "is_active", "is_staff", "is_superuser")


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = (
            "email",
            "nome",
            "cliente",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


class ClienteTemaAdminForm(forms.ModelForm):
    meb_avatar_upload = forms.ImageField(
        required=False,
        help_text="Envie uma nova imagem para o mascote MEB. Formatos comuns (PNG/JPG) são aceitos.",
        label="Upload do avatar do MEB",
    )

    class Meta:
        model = ClienteTema
        fields = "__all__"

    def save(self, commit=True):
        instance: ClienteTema = super().save(commit=False)
        upload = self.cleaned_data.get("meb_avatar_upload")
        if upload:
            cliente_id = instance.cliente_id or getattr(instance.cliente, "id", None)
            if not cliente_id:
                raise ValueError("Selecione um cliente antes de enviar o avatar.")
            suffix = Path(upload.name or "avatar.png").suffix or ".png"
            filename = f"meb/avatars/cliente_{cliente_id}/{uuid4().hex}{suffix}"
            path = default_storage.save(filename, upload)
            url = default_storage.url(path)
            instance.meb_avatar_url = url
        if commit:
            instance.save()
            self.save_m2m()
        return instance
