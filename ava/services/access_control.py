from __future__ import annotations

from django.db.models import Q, QuerySet

from ava.models import Curso
from core.models import Usuario


AVA_EIXO_BYPASS_ROLES = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.SUPER_ADMIN,
}


def user_bypasses_eixo_filter(user) -> bool:
    return getattr(user, "role", None) in AVA_EIXO_BYPASS_ROLES


def course_requires_eixo(curso: Curso) -> bool:
    return curso.eixos.exists()


def user_can_access_course_by_eixo(user, curso: Curso) -> bool:
    if not getattr(user, "is_authenticated", False):
        return not course_requires_eixo(curso)
    if user_bypasses_eixo_filter(user):
        return True
    if not course_requires_eixo(curso):
        return True
    user_eixo_ids = user.eixos.filter(cliente_id=curso.cliente_id, ativo=True).values("id")
    return curso.eixos.filter(id__in=user_eixo_ids, ativo=True).exists()


def course_eixo_block_message(curso: Curso) -> str:
    eixos = ", ".join(curso.eixos.filter(ativo=True).order_by("ordem_exibicao", "nome").values_list("nome", flat=True))
    if not eixos:
        return "Este curso esta restrito por eixo e seu usuario nao possui permissao para acessa-lo."
    return (
        "Este curso esta restrito ao(s) eixo(s) "
        f"{eixos}. Seu usuario nao esta vinculado a nenhum eixo permitido para este curso."
    )


def filter_courses_for_user_by_eixo(queryset: QuerySet[Curso], user) -> QuerySet[Curso]:
    if not getattr(user, "is_authenticated", False):
        return queryset.filter(eixos__isnull=True)
    if user_bypasses_eixo_filter(user):
        return queryset

    user_eixo_ids = user.eixos.filter(ativo=True).values_list("id", flat=True)
    return queryset.filter(Q(eixos__isnull=True) | Q(eixos__in=user_eixo_ids)).distinct()
