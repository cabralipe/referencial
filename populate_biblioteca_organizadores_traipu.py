#!/usr/bin/env python
"""Popula a biblioteca com orientações e links dos organizadores curriculares de Traipu."""

from __future__ import annotations

import os
import unicodedata

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Cliente, Usuario  # noqa: E402
from curriculum.models import GT  # noqa: E402
from library.models import BlocoTexto, Midia  # noqa: E402


BASE_HTML = """
<p><strong>Organizadores Curriculares – Orientações para Contribuição</strong></p>
<p>O Organizador Curricular está sendo realizada exclusivamente de forma on-line.</p>
<p><strong>Como participar:</strong></p>
<ol>
  <li>Acesse o link do documento disponibilizado pela Secretaria;</li>
  <li>Leia atentamente o conteúdo;</li>
  <li>Ao identificar o trecho que deseja contribuir, clique exatamente no ponto do texto;</li>
  <li>Utilize a opção “Adicionar comentário” para registrar sua sugestão, observação ou contribuição.</li>
</ol>
<p><strong>Atenção:</strong></p>
<ul>
  <li>Não baixar o arquivo;</li>
  <li>As contribuições devem ser feitas diretamente na página on-line, por meio dos comentários;</li>
  <li>Comentários enviados fora do documento não serão considerados no processo de sistematização.</li>
</ul>
<p>Sua participação é fundamental para qualificar o documento e fortalecer a construção coletiva da política educacional.</p>
""".strip()


ENTRIES = [
    {
        "gt_nome": "GT – Ensino Fundamental Anos Iniciais",
        "gt_email": "gtfundamental.anosiniciais@hotmail.com",
        "segmento": "FUNDAMENTAL — Anos Iniciais",
        "links": [
            {
                "titulo": "Organizadores Curriculares Anos Iniciais",
                "url": "https://drive.google.com/drive/folders/1sJyhKKLppIHaqbocE-3Lc9RwYKaCRNPb?usp=sharing",
            }
        ],
    },
    {
        "gt_nome": "GT – Ensino Fundamental Anos Finais",
        "gt_email": "gt.anosfinais@hotmail.com",
        "segmento": "FUNDAMENTAL — Anos Finais",
        "links": [
            {
                "titulo": "Organizadores Curriculares Anos Finais",
                "url": "https://drive.google.com/drive/folders/1UWMrKzDBbDpnhPAUUCtjnhRvN8oCqY_4?usp=drive_link",
            }
        ],
    },
    {
        "gt_nome": "GT – Educação Infantil",
        "gt_email": "gtedu.infantil@hotmail.com",
        "segmento": "Educação Infantil",
        "links": [
            {
                "titulo": "Organizador Curricular Educação Infantil",
                "url": "https://drive.google.com/drive/folders/1Gq-KFu5xmI5uHGewtw92k7Qsvq_wBXCT?usp=sharing",
            }
        ],
    },
    {
        "gt_nome": "GT – Educação de Jovens e Adultos (EJA)",
        "gt_email": "gt.eja.1seg@hotmail.com",
        "segmento": "EJA — 1º Segmento",
        "links": [
            {
                "titulo": "Organizador Curricular EJA 1º Segmento",
                "url": "https://drive.google.com/drive/folders/1G4Thq4cde7E88UFts5wewQV8zKFU-2sU?usp=sharing",
            }
        ],
    },
    {
        "gt_nome": "GT – Educação de Jovens e Adultos (EJA) 2° Segmento",
        "gt_email": "gt.eja.2seg@hotmail.com",
        "segmento": "EJA — 2º Segmento",
        "links": [
            {
                "titulo": "Organizador Curricular EJA 2º Segmento",
                "url": "https://drive.google.com/drive/folders/1ni9v_n47yXnPUCVhhef-6y9-9TJKA-FU?usp=sharing",
            }
        ],
    },
    {
        "gt_nome": "GT – Tecnologias Digitais e Computação",
        "gt_email": "gt.tecnologiasdigitaiscomp@hotmail.com",
        "segmento": "BNCC Computação",
        "links": [
            {
                "titulo": "Organizador Curricular BNCC Computação",
                "url": "https://drive.google.com/drive/folders/1CYwnp7GHgT-NXvbQb5Y8n9946a5Cw6P0?usp=sharing",
            }
        ],
    },
]


def normalize(value: str) -> str:
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value


def find_gt(cliente: Cliente, gt_nome: str | None, gt_email: str | None) -> tuple[GT | None, Usuario | None]:
    user = None
    if gt_email:
        user = Usuario.objects.filter(email__iexact=gt_email, cliente=cliente).first()

    gt = None
    if gt_nome:
        gt = GT.objects.filter(cliente=cliente, nome__iexact=gt_nome).first()
        if not gt:
            target = normalize(gt_nome)
            for candidate in GT.objects.filter(cliente=cliente):
                if target in normalize(candidate.nome):
                    gt = candidate
                    break

    if not gt and user:
        user_gts = user.grupos_trabalho.filter(cliente=cliente)
        if user_gts.count() == 1:
            gt = user_gts.first()

    return gt, user


def upsert_bloco(cliente: Cliente, gt: GT, user: Usuario | None, segmento: str) -> BlocoTexto:
    titulo = "Organizadores Curriculares – Orientações para Contribuição"
    conteudo_html = (
        BASE_HTML
        + f"\n<p><strong>Segmento:</strong> {segmento}</p>"
        + "\n<p><strong>Link para acesso ao documento:</strong> consulte o link anexado na biblioteca.</p>"
    )
    tags = ["organizadores-curriculares", "traipu"]

    bloco, created = BlocoTexto.objects.get_or_create(
        cliente=cliente,
        gt=gt,
        titulo=titulo,
        defaults={
            "conteudo_html": conteudo_html,
            "tags": tags,
            "created_by": user,
        },
    )

    if not created:
        changed = False
        if bloco.conteudo_html != conteudo_html:
            bloco.conteudo_html = conteudo_html
            changed = True
        if bloco.tags != tags:
            bloco.tags = tags
            changed = True
        if user and bloco.created_by_id != user.id:
            bloco.created_by = user
            changed = True
        if changed:
            bloco.save(update_fields=["conteudo_html", "tags", "created_by", "updated_at"])

    return bloco


def upsert_midia(cliente: Cliente, gt: GT, user: Usuario | None, titulo: str, url: str, segmento: str) -> Midia:
    descricao = f"Orientações para contribuição — {segmento}."
    tags = ["organizadores-curriculares", "traipu"]

    midia, created = Midia.objects.get_or_create(
        cliente=cliente,
        gt=gt,
        url=url,
        defaults={
            "titulo": titulo,
            "descricao": descricao,
            "tags": tags,
            "uploaded_by": user,
        },
    )

    if not created:
        changed = False
        if midia.titulo != titulo:
            midia.titulo = titulo
            changed = True
        if midia.descricao != descricao:
            midia.descricao = descricao
            changed = True
        if midia.tags != tags:
            midia.tags = tags
            changed = True
        if user and midia.uploaded_by_id != user.id:
            midia.uploaded_by = user
            changed = True
        if changed:
            midia.save(update_fields=["titulo", "descricao", "tags", "uploaded_by", "updated_at"])

    return midia


def main():
    cliente = Cliente.objects.filter(slug="secretaria-municipal-de-educacao-traipu").first()
    if not cliente:
        raise SystemExit("Cliente com slug 'secretaria-municipal-de-educacao-traipu' não encontrado.")

    print(f"Cliente: {cliente.nome} (id={cliente.id})")

    for entry in ENTRIES:
        gt_nome = entry.get("gt_nome")
        gt_email = entry.get("gt_email")
        segmento = entry["segmento"]
        gt, user = find_gt(cliente, gt_nome, gt_email)

        if not gt:
            print(f"[SKIP] GT não encontrado para '{gt_nome}' ({gt_email or 'sem email'}).")
            continue

        if user and not gt.membros.filter(id=user.id).exists():
            gt.membros.add(user)
            print(f"[INFO] Adicionado {user.email} como membro do GT '{gt.nome}'.")

        bloco = upsert_bloco(cliente, gt, user, segmento)
        print(f"[OK] Bloco '{bloco.titulo}' para GT '{gt.nome}'.")

        for link in entry["links"]:
            midia = upsert_midia(cliente, gt, user, link["titulo"], link["url"], segmento)
            print(f"[OK] Link '{midia.titulo}' para GT '{gt.nome}'.")


if __name__ == "__main__":
    main()
