from decimal import Decimal

import pytest

from ava.models import Curso
from core.models import AuditLog


@pytest.mark.django_db
def test_audit_log_snapshot_serializes_decimal_fields(cliente):
    curso = Curso.objects.create(
        cliente=cliente,
        titulo="Curso com decimal",
        slug="curso-com-decimal",
        nota_minima=Decimal("82.25"),
    )

    log = AuditLog.raw_objects.get(
        entidade="ava.Curso",
        entidade_id=str(curso.pk),
        acao="created",
    )

    assert log.diff_json["current"]["nota_minima"] == "82.25"
