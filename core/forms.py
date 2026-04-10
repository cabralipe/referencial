"""Formulários customizados para o Django Admin."""

from pathlib import Path
from uuid import uuid4

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.files.storage import default_storage

from .models import ClienteTema, Usuario


def _sync_user_clientes(user: Usuario, cleaned_data: dict) -> Usuario:
    role = cleaned_data.get("role", user.role)
    cliente = cleaned_data.get("cliente", user.cliente)
    clientes = cleaned_data.get("clientes")

    if role == Usuario.Role.SUPER_ADMIN:
        user.clientes.clear()
        return user

    selected_clientes = []
    if clientes is not None:
        selected_clientes = list(clientes)
    elif user.pk:
        selected_clientes = list(user.clientes.all())

    if cliente and all(item.id != cliente.id for item in selected_clientes):
        selected_clientes.append(cliente)

    if selected_clientes:
        user.clientes.set(selected_clientes)
    elif cliente:
        user.clientes.set([cliente])
    else:
        user.clientes.clear()

    if not user.cliente_id and selected_clientes:
        user.cliente = selected_clientes[0]
        user.save(update_fields=["cliente"])
    return user


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            "email",
            "nome",
            "cliente",
            "clientes",
            "escola",
            "role",
            "seguimento",
            "is_active",
            "is_staff",
            "is_superuser",
        )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        cliente = cleaned_data.get("cliente")
        clientes = cleaned_data.get("clientes")

        if role != Usuario.Role.SUPER_ADMIN and not cliente and clientes:
            cleaned_data["cliente"] = clientes.first()
        if role == Usuario.Role.SUPER_ADMIN:
            cleaned_data["cliente"] = None
            if "clientes" in self.fields:
                cleaned_data["clientes"] = self.fields["clientes"].queryset.none()
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user = _sync_user_clientes(user, self.cleaned_data)
        return user


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = (
            "email",
            "nome",
            "cliente",
            "clientes",
            "escola",
            "role",
            "seguimento",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        cliente = cleaned_data.get("cliente")
        clientes = cleaned_data.get("clientes")

        if role != Usuario.Role.SUPER_ADMIN and not cliente and clientes:
            cleaned_data["cliente"] = clientes.first()
        if role == Usuario.Role.SUPER_ADMIN:
            cleaned_data["cliente"] = None
            if "clientes" in self.fields:
                cleaned_data["clientes"] = self.fields["clientes"].queryset.none()
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user = _sync_user_clientes(user, self.cleaned_data)
        return user


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
