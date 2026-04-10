import pytest

from bank.models import PlanoPublicado
from core.models import Cliente, Usuario
from courses.models import Curso, CursoModulo, CursoProgresso, CursoProgressoItem, PlanoAula
from courses.services.certification_service import evaluate_certification
from documents.models import PlanoMetaPPP


@pytest.mark.django_db
def test_certification_service_rules(cliente, usuario):
    curso = Curso.objects.create(
        cliente=cliente,
        nome="Curso PLACI",
        publicado=True,
        regras_certificacao_json={
            "percentual_minimo_conclusao": 80,
            "numero_minimo_planos": 1,
            "presenca_obrigatoria": False,
            "entrega_final_obrigatoria": True,
            "publicacao_no_banco_obrigatoria": True,
        },
    )
    modulo = CursoModulo.objects.create(
        cliente=cliente,
        curso=curso,
        titulo="Entrega",
        ordem=1,
        tipo=CursoModulo.Tipo.ENTREGA_FINAL,
    )
    item = modulo.itens.create(cliente=cliente, ordem=1, tipo="CHECKLIST", titulo="Checklist final")
    progresso = CursoProgresso.objects.create(cliente=cliente, curso=curso, usuario=usuario, percentual=80)
    CursoProgressoItem.objects.create(
        cliente=cliente,
        progresso=progresso,
        item=item,
        referencia_tipo="curso_item",
        referencia_id=str(item.id),
    )
    plano = PlanoAula.objects.create(
        cliente=cliente,
        curso=curso,
        autor=usuario,
        escola="Escola A",
        status=PlanoAula.Status.EM_REVISAO,
    )
    PlanoPublicado.objects.create(
        cliente=cliente,
        plano=plano,
        publicado_por=usuario,
        status_curadoria=PlanoPublicado.CuradoriaStatus.APROVADO,
    )
    result = evaluate_certification(curso, usuario.id, publicados_no_banco=1)
    assert result.approved is True


@pytest.mark.django_db
def test_planos_estruturados_autosave_endpoint(auth_client, cliente, usuario):
    curso = Curso.objects.create(cliente=cliente, nome="Curso Autosave", publicado=True)
    plano = PlanoAula.objects.create(cliente=cliente, curso=curso, autor=usuario)

    response = auth_client.patch(
        f"/api/v1/planos-estruturados/{plano.id}/autosave",
        {"metodologia": "Aprendizagem por projetos", "avaliacao": "Rubrica formativa"},
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metodologia"] == "Aprendizagem por projetos"
    assert payload["avaliacao"] == "Rubrica formativa"


@pytest.mark.django_db
def test_relatorio_por_meta_ppp(auth_client, cliente, usuario):
    curso = Curso.objects.create(cliente=cliente, nome="Curso Documento", publicado=True)
    meta = PlanoMetaPPP.objects.create(cliente=cliente, codigo="M1", titulo="Meta 1")
    PlanoAula.objects.create(
        cliente=cliente,
        curso=curso,
        autor=usuario,
        escola="Escola Alfa",
        metas_ppp=["M1"],
    )
    PlanoAula.objects.create(
        cliente=cliente,
        curso=curso,
        autor=usuario,
        escola="Escola Alfa",
        metas_ppp=["M1"],
    )

    response = auth_client.get(f"/api/v1/documentos/ppp-metas/{meta.id}/relatorio")
    assert response.status_code == 200
    body = response.json()
    assert body["total_planos"] == 2
    assert body["por_escola"][0]["escola"] == "Escola Alfa"
    assert body["por_escola"][0]["total"] == 2


@pytest.mark.django_db
def test_admin_analytics_endpoint_requires_admin(api_client, cliente, usuario):
    normal_user = Usuario.objects.create_user(
        email="membro@teste.com",
        password="senha123",
        nome="Membro",
        cliente=cliente,
        role=Usuario.Role.MEMBRO_GT,
    )
    api_client.force_authenticate(normal_user)
    forbidden = api_client.get("/api/v1/analytics/admin")
    assert forbidden.status_code == 403

    api_client.force_authenticate(usuario)
    ok = api_client.get("/api/v1/analytics/admin")
    assert ok.status_code == 200


@pytest.mark.django_db
def test_admin_analytics_endpoint_traz_campos_enriquecidos(api_client, cliente, usuario):
    curso = Curso.objects.create(cliente=cliente, nome="Curso Analytics", publicado=True)
    PlanoAula.objects.create(
        cliente=cliente,
        curso=curso,
        autor=usuario,
        escola="Escola Centro",
        componente_curricular="Matematica",
        etapa_modalidade="Fundamental",
        status=PlanoAula.Status.PUBLICADO,
    )
    PlanoAula.objects.create(
        cliente=cliente,
        curso=curso,
        autor=usuario,
        escola="",
        componente_curricular="",
        etapa_modalidade="",
        status=PlanoAula.Status.EM_REVISAO,
    )
    CursoProgresso.objects.create(cliente=cliente, curso=curso, usuario=usuario, percentual=100)
    PlanoPublicado.objects.create(
        cliente=cliente,
        plano=PlanoAula.objects.filter(cliente=cliente).first(),
        publicado_por=usuario,
        status_curadoria=PlanoPublicado.CuradoriaStatus.APROVADO,
    )

    api_client.force_authenticate(usuario)
    response = api_client.get("/api/v1/analytics/admin")
    assert response.status_code == 200

    body = response.json()
    assert body["totais"]["total_planos"] == 2
    assert body["totais"]["autores_ativos"] == 1
    assert "producao_por_status" in body
    assert "top_autores" in body
    assert body["top_autores"][0]["autor_id"] == usuario.id
    assert any(item["escola"] == "Nao informado" for item in body["engajamento_por_escola"])


@pytest.mark.django_db
def test_admin_analytics_endpoint_respeita_scope_por_header_para_admin_cliente(api_client, django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente Analytics A", slug="analytics-a")
    cliente_b = Cliente.objects.create(nome="Cliente Analytics B", slug="analytics-b")

    admin = django_user_model.objects.create_user(
        email="admin.analytics@teste.com",
        password="senha123",
        nome="Admin Analytics",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
    )
    admin.clientes.add(cliente_b)

    curso_a = Curso.objects.create(cliente=cliente_a, nome="Curso A", publicado=True)
    curso_b = Curso.objects.create(cliente=cliente_b, nome="Curso B", publicado=True)
    PlanoAula.objects.create(
        cliente=cliente_a,
        curso=curso_a,
        autor=admin,
        escola="Escola A",
        status=PlanoAula.Status.EM_REVISAO,
    )
    PlanoAula.objects.create(
        cliente=cliente_b,
        curso=curso_b,
        autor=admin,
        escola="Escola B",
        status=PlanoAula.Status.PUBLICADO,
    )

    api_client.force_authenticate(admin)
    response = api_client.get("/api/v1/analytics/admin", HTTP_X_CLIENTE_ID=str(cliente_b.id))
    assert response.status_code == 200

    body = response.json()
    assert body["totais"]["total_planos"] == 1
    assert body["engajamento_por_escola"][0]["escola"] == "Escola B"
