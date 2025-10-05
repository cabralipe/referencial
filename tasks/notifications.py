"""Tarefas relacionadas a notificações."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from celery import shared_task

from notifications.models import Notificacao


@shared_task(name="tasks.notifications.send_email_notification")
def send_email_notification(notification_id: int) -> None:
    notification = Notificacao.objects.filter(pk=notification_id, is_deleted=False).select_related("usuario").first()
    if not notification or not notification.usuario.email:
        return

    subject = f"Nova notificação: {notification.tipo}"
    body = render_to_string(
        "emails/notification.txt",
        {"notification": notification},
    )
    send_mail(
        subject,
        body,
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        [notification.usuario.email],
        fail_silently=True,
    )
