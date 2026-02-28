"""Regras de curadoria para publicacoes do banco."""

from bank.models import PlanoPublicado


def apply_curation_decision(plano_publicado: PlanoPublicado, approved: bool) -> PlanoPublicado:
    plano_publicado.status_curadoria = (
        PlanoPublicado.CuradoriaStatus.APROVADO if approved else PlanoPublicado.CuradoriaStatus.REJEITADO
    )
    plano_publicado.save(update_fields=["status_curadoria", "updated_at"])
    return plano_publicado

