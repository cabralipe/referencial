"""Funções auxiliares para permissões e configurações."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework.exceptions import PermissionDenied

from .models import Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, Usuario


def usuario_e_membro_do_gt(usuario: Usuario, gt_id: int) -> bool:
    if not usuario.is_authenticated:
        return False
    if usuario.role in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}:
        return True
    from curriculum.models import GT  # importação tardia

    try:
        gt = GT.objects.get(pk=gt_id)
    except GT.DoesNotExist:
        return False
    return gt.membros.filter(pk=usuario.pk).exists()


def coletar_contexto_do_cliente(cliente: Cliente) -> Dict[str, Any]:
    configs = {
        cfg.chave: cfg.valor_texto
        for cfg in ClienteConfig.raw_objects.filter(cliente=cliente, is_deleted=False)
    }
    flags = {
        flag.flag: flag.ativo
        for flag in ClienteFeatureFlag.raw_objects.filter(cliente=cliente, is_deleted=False)
    }
    tema = (
        ClienteTema.raw_objects.filter(cliente=cliente, is_deleted=False).values(
            "logo_url",
            "cor_primaria",
            "cor_secundaria",
            "rodape_html",
            "cabecalho_html",
        ).first()
        or {}
    )
    return {
        "cliente": {
            "id": cliente.id,
            "nome": cliente.nome,
            "slug": cliente.slug,
        },
        "configs": configs,
        "flags": flags,
        "tema": tema,
    }


def obter_config(cliente: Cliente, chave: str, default: Optional[str] = None) -> Optional[str]:
    registro = ClienteConfig.raw_objects.filter(cliente=cliente, chave=chave, is_deleted=False).first()
    if registro:
        return registro.valor_texto
    return default


def flag_ativa(cliente: Cliente, flag: str) -> bool:
    registro = ClienteFeatureFlag.raw_objects.filter(cliente=cliente, flag=flag, is_deleted=False).first()
    return bool(registro and registro.ativo)


def verificar_flag(request, flag: str) -> None:
    cliente = getattr(request, "cliente_id", None)
    if cliente is None and request.user.is_authenticated:
        cliente = getattr(request.user, "cliente_id", None)
    if cliente is None:
        raise PermissionDenied("Cliente não associado")
    from core.models import Cliente

    cliente_obj = Cliente.objects.filter(pk=cliente).first()
    if not cliente_obj:
        raise PermissionDenied("Cliente não encontrado")
    if not flag_ativa(cliente_obj, flag):
        raise PermissionDenied("Funcionalidade desabilitada para este cliente")
