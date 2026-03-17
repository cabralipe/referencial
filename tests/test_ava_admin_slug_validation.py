import pytest

from ava.admin import CursoAdminForm
from ava.models import Curso
from core.models import Cliente


@pytest.mark.django_db
def test_curso_admin_form_rejeita_slug_duplicado_de_registro_soft_deleted():
    cliente = Cliente.objects.create(nome="Cliente AVA", slug="cliente-ava")
    curso = Curso.raw_objects.create(
        cliente=cliente,
        titulo="Curso Original",
        slug="curso-original",
    )
    curso.is_deleted = True
    curso.save(update_fields=["is_deleted", "updated_at"])

    form = CursoAdminForm(
        data={
            "cliente": cliente.id,
            "titulo": "Curso Novo",
            "slug": "curso-original",
            "status": Curso.Status.RASCUNHO,
        }
    )

    assert not form.is_valid()
    assert "slug" in form.errors
