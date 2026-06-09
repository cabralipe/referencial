from __future__ import annotations

from django.db.models import QuerySet

from ava.models import Atividade, Curso, CursoModulo
from core.models import Usuario


AVA_EIXO_BYPASS_ROLES = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.SUPER_ADMIN,
}

AVA_EIXO_RESTRICTABLE_ROLES = {
    Usuario.Role.DIRETOR,
    Usuario.Role.COORDENADOR_PEDAGOGICO,
    Usuario.Role.PROFESSOR,
    Usuario.Role.ARTICULADOR,
    Usuario.Role.REVISOR,
    Usuario.Role.MEMBRO_GT,
    Usuario.Role.LEITOR,
}


def user_bypasses_eixo_filter(user) -> bool:
    return getattr(user, "role", None) in AVA_EIXO_BYPASS_ROLES


def course_requires_eixo(curso: Curso) -> bool:
    return curso.eixos.exists()


def eixo_restriction_applies_to_user(user, restriction_roles) -> bool:
    role = getattr(user, "role", None)
    if role in AVA_EIXO_BYPASS_ROLES:
        return False
    roles = [item for item in (restriction_roles or []) if item in AVA_EIXO_RESTRICTABLE_ROLES]
    if not roles:
        return True
    return role in roles


def user_can_access_course_by_eixo(user, curso: Curso) -> bool:
    if not getattr(user, "is_authenticated", False):
        return not course_requires_eixo(curso)
    if user_bypasses_eixo_filter(user):
        return True
    if not eixo_restriction_applies_to_user(user, getattr(curso, "eixos_restricao_roles", [])):
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
    return queryset.distinct()


def module_requires_eixo(modulo: CursoModulo) -> bool:
    return modulo.eixos.exists()


def user_can_access_module_by_eixo(user, modulo: CursoModulo) -> bool:
    if not getattr(user, "is_authenticated", False):
        return not module_requires_eixo(modulo)
    if user_bypasses_eixo_filter(user):
        return True
    if not eixo_restriction_applies_to_user(user, getattr(modulo, "eixos_restricao_roles", [])):
        return True
    if not module_requires_eixo(modulo):
        return True
    user_eixo_ids = user.eixos.filter(cliente_id=modulo.cliente_id, ativo=True).values("id")
    return modulo.eixos.filter(id__in=user_eixo_ids, ativo=True).exists()


def module_eixo_block_message(modulo: CursoModulo) -> str:
    eixos = ", ".join(modulo.eixos.filter(ativo=True).order_by("ordem_exibicao", "nome").values_list("nome", flat=True))
    if not eixos:
        return "Este modulo esta restrito por eixo e seu usuario nao possui permissao para acessa-lo."
    return (
        "Este modulo esta restrito ao(s) eixo(s) "
        f"{eixos}. Seu usuario nao esta vinculado a nenhum eixo permitido para este modulo."
    )


def activity_requires_eixo(atividade: Atividade) -> bool:
    return atividade.eixos.exists()


def user_can_access_activity_by_eixo(user, atividade: Atividade) -> bool:
    if not getattr(user, "is_authenticated", False):
        return not activity_requires_eixo(atividade)
    if user_bypasses_eixo_filter(user):
        return True
    if not eixo_restriction_applies_to_user(user, getattr(atividade, "eixos_restricao_roles", [])):
        return True
    if not activity_requires_eixo(atividade):
        return True
    user_eixo_ids = user.eixos.filter(cliente_id=atividade.cliente_id, ativo=True).values("id")
    return atividade.eixos.filter(id__in=user_eixo_ids, ativo=True).exists()


def activity_eixo_block_message(atividade: Atividade) -> str:
    eixos = ", ".join(atividade.eixos.filter(ativo=True).order_by("ordem_exibicao", "nome").values_list("nome", flat=True))
    if not eixos:
        return "Esta atividade esta restrita por eixo e seu usuario nao possui permissao para acessa-la."
    return (
        "Esta atividade esta restrita ao(s) eixo(s) "
        f"{eixos}. Seu usuario nao esta vinculado a nenhum eixo permitido para esta atividade."
    )
