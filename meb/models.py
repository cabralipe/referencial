"""Modelos do chat do mascote MEB."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class MebThread(TenantModel):
    """Canal individual de conversa entre um usuário e os administradores."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meb_threads",
    )

    class Meta:
        verbose_name = "Thread do MEB"
        verbose_name_plural = "Threads do MEB"
        unique_together = ("cliente", "usuario")
        ordering = ("-updated_at",)

    def __str__(self) -> str:  # pragma: no cover - legibilidade no admin
        return f"Thread MEB #{self.pk} - {self.usuario}"


class MebMessage(TenantModel):
    """Mensagens trocadas no chat."""

    class Origem(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        ADMIN = "admin", "Admin"
        MASCOTE = "meb", "MEB"
        SISTEMA = "sistema", "Sistema"

    thread = models.ForeignKey(
        MebThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meb_messages",
    )
    origem = models.CharField(
        max_length=20,
        choices=Origem.choices,
        default=Origem.CLIENTE,
    )
    conteudo = models.TextField()

    class Meta:
        verbose_name = "Mensagem do MEB"
        verbose_name_plural = "Mensagens do MEB"
        ordering = ("created_at", "id")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.get_origem_display()} - {self.conteudo[:30]}"
