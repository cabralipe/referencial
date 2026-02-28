import pytest

from core.models import Cliente
from dynamicforms.models import FormularioDinamico
from courses.models import (
    Curso,
    CursoItem,
    CursoModulo,
    CursoParticipacao,
    CursoProgresso,
    CursoProgressoItem,
    PlanoAulaPublicacao,
    PlanoAulaResposta,
)
from courses.serializers import ensure_plano_aula_template


def _create_course(cliente, *, publicado=True, regras=None):
    curso = Curso.objects.create(
        cliente=cliente,
        nome="Curso Referencial e PPP",
        categoria=Curso.Categoria.AVAMEC,
        descricao="Curso estilo AVAMEC",
        objetivos="Objetivos do curso",
        carga_horaria_total=60,
        carga_presencial=8,
        carga_sincrona=14,
        carga_producao=38,
        publicado=publicado,
        regras_certificacao_json=regras or {},
    )
    modulo = CursoModulo.objects.create(
        cliente=cliente,
        curso=curso,
        titulo="Módulo 1",
        ordem=1,
        tipo=CursoModulo.Tipo.MODULO,
    )
    item = CursoItem.objects.create(
        cliente=cliente,
        modulo=modulo,
        ordem=1,
        tipo=CursoItem.Tipo.TEXTO,
        titulo="Texto base",
        payload_json={"html": "<p>Base</p>"},
    )
    return curso, modulo, item


def _required_campos_payload():
    return {
        "escola": "Escola X",
        "professor": "Professor Y",
        "etapa_modalidade": "Anos Finais",
        "componente_curricular": "Matemática",
        "unidade_tematica": "Números",
        "habilidades_referencial": "EF08MA01",
        "objetivos_aprendizagem": "Resolver problemas com frações",
        "conteudos": "Frações e equivalência",
        "metodologia": "Roda de conversa + prática",
        "recursos": "Quadro e fichas",
        "avaliacao": "Rubrica e observação",
        "estrategias_recomposicao": "Atividades graduadas",
        "estrategias_inclusivas_aee": "Adaptação visual",
        "referencias": "Referencial Curricular",
    }


@pytest.mark.django_db
def test_usuario_cliente_a_nao_ve_curso_cliente_b(api_client, cliente, membro_gt):
    outro_cliente = Cliente.objects.create(nome="Outro", slug="outro")
    curso_a, _mod_a, _item_a = _create_course(cliente, publicado=True)
    curso_b, _mod_b, _item_b = _create_course(outro_cliente, publicado=True)

    membro_gt.cliente = cliente
    membro_gt.save(update_fields=["cliente"])
    api_client.force_authenticate(membro_gt)

    resp_list = api_client.get("/api/v1/cursos")
    assert resp_list.status_code == 200
    payload = resp_list.json()
    rows = payload.get("results", payload)
    ids = {row["id"] for row in rows}
    assert curso_a.id in ids
    assert curso_b.id not in ids

    resp_detail = api_client.get(f"/api/v1/cursos/{curso_b.id}")
    assert resp_detail.status_code in {403, 404}


@pytest.mark.django_db
def test_admin_pode_patch_curso_usuario_comum_recebe_403(api_client, cliente, usuario, membro_gt):
    curso, _modulo, _item = _create_course(cliente, publicado=False)

    api_client.force_authenticate(usuario)
    resp_admin = api_client.patch(
        f"/api/v1/cursos/{curso.id}",
        {"publicado": True, "regras_certificacao_json": {"min_planos": "2", "min_sincronos": -10}},
        format="json",
    )
    assert resp_admin.status_code == 200
    body = resp_admin.json()
    assert body["publicado"] is True
    assert body["regras_certificacao"]["min_planos"] == 2
    assert body["regras_certificacao"]["min_sincronos"] == 0

    membro_gt.cliente = cliente
    membro_gt.save(update_fields=["cliente"])
    api_client.force_authenticate(membro_gt)
    resp_user = api_client.patch(f"/api/v1/cursos/{curso.id}", {"descricao": "hack"}, format="json")
    assert resp_user.status_code == 403


@pytest.mark.django_db
def test_post_progresso_nao_permite_item_de_outro_curso_ou_cliente(api_client, cliente, membro_gt):
    curso, _modulo, item = _create_course(cliente, publicado=True)
    outro_curso, _mod2, item_outro = _create_course(cliente, publicado=True)
    outro_cliente = Cliente.objects.create(nome="Cliente B", slug="cliente-b")
    curso_b, _mod_b, item_b = _create_course(outro_cliente, publicado=True)
    assert outro_curso.id != curso.id

    membro_gt.cliente = cliente
    membro_gt.save(update_fields=["cliente"])
    api_client.force_authenticate(membro_gt)

    ok_resp = api_client.post(f"/api/v1/cursos/{curso.id}/progresso", {"item_id": item.id}, format="json")
    assert ok_resp.status_code == 200

    bad_same_cliente = api_client.post(
        f"/api/v1/cursos/{curso.id}/progresso",
        {"item_id": item_outro.id},
        format="json",
    )
    assert bad_same_cliente.status_code == 400

    bad_other_cliente = api_client.post(
        f"/api/v1/cursos/{curso.id}/progresso",
        {"item_id": item_b.id},
        format="json",
    )
    assert bad_other_cliente.status_code == 400

    progresso = CursoProgresso.objects.get(curso=curso, usuario=membro_gt)
    assert int(progresso.percentual) > 0


@pytest.mark.django_db
def test_publicacao_banco_so_tutor_admin_aprova(api_client, cliente, usuario, articulador, membro_gt):
    curso, _modulo, _item = _create_course(cliente, publicado=True)
    formulario = ensure_plano_aula_template(cliente.id)
    plano = PlanoAulaResposta.objects.create(
        cliente=cliente,
        curso=curso,
        usuario=membro_gt,
        formulario=formulario,
        status=PlanoAulaResposta.Status.ENVIADO,
        compartilhado_banco=True,
        dados_cache_json=_required_campos_payload(),
    )
    publicacao = PlanoAulaPublicacao.objects.create(
        cliente=cliente,
        autor=membro_gt,
        resposta_formulario=plano,
        status=PlanoAulaPublicacao.Status.ENVIADO,
        payload_json=_required_campos_payload(),
    )

    api_client.force_authenticate(membro_gt)
    resp_forbidden = api_client.patch(
        f"/api/v1/banco-planos/{publicacao.id}",
        {"status": "PUBLICADO"},
        format="json",
    )
    assert resp_forbidden.status_code == 403

    api_client.force_authenticate(articulador)
    resp_tutor = api_client.patch(
        f"/api/v1/banco-planos/{publicacao.id}",
        {"status": "PUBLICADO"},
        format="json",
    )
    assert resp_tutor.status_code == 200
    assert resp_tutor.json()["status"] == "PUBLICADO"

    api_client.force_authenticate(usuario)
    resp_list = api_client.get("/api/v1/banco-planos?componente=Matemática")
    assert resp_list.status_code == 200
    payload = resp_list.json()
    rows = payload.get("results", payload)
    assert any(row["id"] == publicacao.id for row in rows)


@pytest.mark.django_db
def test_certificacao_status_reflete_regras_elegibilidade(api_client, cliente, membro_gt):
    regras = {
        "presenca_presencial_obrigatoria": True,
        "min_sincronos": 4,
        "min_planos": 1,
        "entrega_final_obrigatoria": True,
        "compartilhar_banco_obrigatorio": True,
    }
    curso = Curso.objects.create(
        cliente=cliente,
        nome="Curso Certificação",
        publicado=True,
        regras_certificacao_json=regras,
    )
    modulo_entrega = CursoModulo.objects.create(
        cliente=cliente,
        curso=curso,
        titulo="Entrega Final",
        ordem=99,
        tipo=CursoModulo.Tipo.ENTREGA_FINAL,
    )
    item_entrega = CursoItem.objects.create(
        cliente=cliente,
        modulo=modulo_entrega,
        ordem=1,
        tipo=CursoItem.Tipo.CHECKLIST,
        titulo="Entrega",
        payload_json={},
    )
    formulario = ensure_plano_aula_template(cliente.id)
    plano = PlanoAulaResposta.objects.create(
        cliente=cliente,
        curso=curso,
        usuario=membro_gt,
        formulario=formulario,
        status=PlanoAulaResposta.Status.ENVIADO,
        compartilhado_banco=True,
        dados_cache_json=_required_campos_payload(),
    )
    PlanoAulaPublicacao.objects.create(
        cliente=cliente,
        autor=membro_gt,
        resposta_formulario=plano,
        status=PlanoAulaPublicacao.Status.PUBLICADO,
        payload_json=_required_campos_payload(),
    )
    CursoParticipacao.objects.create(
        cliente=cliente,
        curso=curso,
        usuario=membro_gt,
        presenca_presencial=True,
        encontros_sincronos_presentes=4,
    )
    progresso = CursoProgresso.objects.create(cliente=cliente, curso=curso, usuario=membro_gt, percentual=100)
    CursoProgressoItem.objects.create(
        cliente=cliente,
        progresso=progresso,
        item=item_entrega,
        referencia_tipo="curso_item",
        referencia_id=str(item_entrega.id),
    )

    membro_gt.cliente = cliente
    membro_gt.save(update_fields=["cliente"])
    api_client.force_authenticate(membro_gt)

    resp = api_client.get(f"/api/v1/cursos/{curso.id}/certificacao/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pode_emitir_certificado"] is True
    assert body["checks"]["min_planos"]["ok"] is True
    assert body["checks"]["entrega_final"]["ok"] is True
    assert body["checks"]["compartilhar_banco"]["ok"] is True

    emit_resp = api_client.post(f"/api/v1/cursos/{curso.id}/certificacao/emitir", {}, format="json")
    assert emit_resp.status_code in {200, 201}
    assert emit_resp.json()["stub"] is True


@pytest.mark.django_db
def test_planos_aula_create_and_enviar_cria_template_e_publicacao(api_client, cliente, membro_gt):
    curso, _modulo, _item = _create_course(cliente, publicado=True)
    membro_gt.cliente = cliente
    membro_gt.save(update_fields=["cliente"])
    api_client.force_authenticate(membro_gt)

    create_resp = api_client.post(
        "/api/v1/planos-aula",
        {
            "curso": curso.id,
            "titulo": "Plano de Aula 1",
            "campos": _required_campos_payload(),
        },
        format="json",
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    plano_id = body["id"]
    assert FormularioDinamico.objects.filter(cliente=cliente, nome="Plano de Aula Padrão").exists()

    send_resp = api_client.post(
        f"/api/v1/planos-aula/{plano_id}/enviar",
        {"compartilhar_no_banco": True},
        format="json",
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["plano"]["status"] == "ENVIADO"
    assert send_resp.json()["publicacao"]["status"] == "ENVIADO"
