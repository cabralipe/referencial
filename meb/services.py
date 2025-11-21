"""Serviços auxiliares do chat do mascote MEB."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import MebMessage, MebThread

WELCOME_MESSAGE = (
    "Olá! Eu sou o MEB e fico aqui para registrar suas dúvidas. "
    "Sempre que precisar, é só me chamar que aviso os administradores."
)

DEFAULT_ESCALATION_MESSAGE = (
    "Anotei sua mensagem e já encaminhei para a equipe do seu cliente. "
    "Assim que alguém responder eu te aviso por aqui."
)


@dataclass(frozen=True)
class SimpleAnswerRule:
    required: tuple[str, ...]
    any_of: tuple[str, ...] = ()
    answer: str = ""

    def matches(self, normalized: str) -> bool:
        if not all(token in normalized for token in self.required):
            return False
        if self.any_of and not any(token in normalized for token in self.any_of):
            return False
        return True


SIMPLE_RULES: tuple[SimpleAnswerRule, ...] = (
    SimpleAnswerRule(
        required=("login",),
        any_of=("senha", "esqueci", "recuperar", "trocar"),
        answer="Para recuperar ou trocar sua senha clique em “Esqueci minha senha” na tela de login e siga o passo a passo enviado por e-mail.",
    ),
    SimpleAnswerRule(
        required=("tarefas",),
        any_of=("enviar", "submeter", "mandar", "responder"),
        answer="Acesse o menu Tarefas, escolha o GT e clique na tarefa desejada para preencher as respostas ou anexar arquivos.",
    ),
    SimpleAnswerRule(
        required=("prazo",),
        answer="Os prazos das atividades ficam destacados no topo das tarefas e também podem ser acompanhados no painel inicial.",
    ),
    SimpleAnswerRule(
        required=("biblioteca",),
        answer="A Biblioteca fica no menu lateral e reúne todos os materiais enviados pelos administradores do seu cliente.",
    ),
    SimpleAnswerRule(
        required=("ajuda",),
        any_of=("duvida", "dúvida", "contato", "falar"),
        answer="Use este chat para registrar dúvidas rápidas e acompanhe as respostas quando os administradores retornarem.",
    ),
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    return " ".join(ascii_text.lower().split())


def build_auto_reply(message: str) -> Optional[str]:
    """Retorna uma resposta simples do MEB quando possível."""
    normalized = _normalize(message)
    if not normalized:
        return None
    for rule in SIMPLE_RULES:
        if rule.matches(normalized):
            return rule.answer
    if any(token in normalized for token in ("obrigado", "valeu", "perfeito")):
        return "Fico feliz em ajudar! Se precisar de algo a mais é só escrever por aqui."
    return None


def ensure_thread_for_user(usuario, cliente_id: Optional[int] = None) -> MebThread:
    """Garante que exista uma thread para o usuário, criando com mensagem de boas-vindas."""
    cliente_id = cliente_id or getattr(usuario, "cliente_id", None)
    if not cliente_id:
        raise ValueError("Usuário sem cliente associado não pode iniciar o chat do MEB.")
    thread, created = MebThread.objects.get_or_create(
        cliente_id=cliente_id,
        usuario=usuario,
        defaults={"cliente_id": cliente_id},
    )
    if created:
        MebMessage.objects.create(
            cliente_id=cliente_id,
            thread=thread,
            origem=MebMessage.Origem.MASCOTE,
            conteudo=WELCOME_MESSAGE,
        )
        thread.updated_at = timezone.now()
        thread.save(update_fields=["updated_at"])
    return thread


def auto_reply_for_message(thread: MebThread, message: str) -> MebMessage:
    """Cria uma resposta automática do mascote."""
    resposta = build_auto_reply(message) or DEFAULT_ESCALATION_MESSAGE
    reply = MebMessage.objects.create(
        cliente_id=thread.cliente_id,
        thread=thread,
        origem=MebMessage.Origem.MASCOTE,
        conteudo=resposta,
    )
    thread.updated_at = timezone.now()
    thread.save(update_fields=["updated_at"])
    return reply


def deliver_admin_broadcast(
    *,
    cliente_id: int,
    autor,
    conteudo: str,
    usuario_ids: Optional[Iterable[int]] = None,
    gt_ids: Optional[Iterable[int]] = None,
    include_all: bool = False,
) -> int:
    """Envia uma mensagem administrativa para vários destinatários via MEB."""
    UserModel = get_user_model()
    base_queryset = UserModel.objects.filter(cliente_id=cliente_id, is_active=True)

    recipients = base_queryset.none()
    if include_all:
        recipients = base_queryset
    else:
        if usuario_ids:
            recipients = recipients.union(base_queryset.filter(id__in=list(usuario_ids)))
        if gt_ids:
            recipients = recipients.union(
                base_queryset.filter(grupos_trabalho__id__in=list(gt_ids))
            )

    recipients = recipients.exclude(id=getattr(autor, "id", None)).distinct()
    if not recipients.exists():
        return 0

    delivered = 0
    now = timezone.now()
    for usuario in recipients:
        thread = ensure_thread_for_user(usuario, cliente_id)
        MebMessage.objects.create(
            cliente_id=cliente_id,
            thread=thread,
            autor=autor,
            origem=MebMessage.Origem.ADMIN,
            conteudo=conteudo,
        )
        thread.updated_at = now
        thread.save(update_fields=["updated_at"])
        delivered += 1
    return delivered


__all__ = ["ensure_thread_for_user", "auto_reply_for_message", "build_auto_reply", "deliver_admin_broadcast"]
