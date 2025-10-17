"""Formulários customizados para o Django Admin."""

from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import Usuario


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
