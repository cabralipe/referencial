"""Importa os objetivos oficiais do Referencial a partir de CSV ou JSON.

Os objetivos nunca são inventados pelo sistema: eles vêm de um arquivo
fornecido pela rede. O ``codigo`` é a chave estável — reimportar o arquivo
atualiza título/texto/ordem sem duplicar registro.

Exemplos:

    python manage.py importar_objetivos_referencial --cliente prefeitura objetivos.csv
    python manage.py importar_objetivos_referencial --cliente 3 objetivos.json --desativar-ausentes
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ava.models.gt_sala import ObjetivoReferencial
from core.models import Cliente


class Command(BaseCommand):
    help = "Importa/atualiza os objetivos oficiais do Referencial de um arquivo CSV ou JSON."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho do arquivo CSV (codigo;titulo;texto;ordem) ou JSON.")
        parser.add_argument(
            "--cliente",
            required=True,
            help="ID ou slug do município (core.Cliente) que receberá os objetivos.",
        )
        parser.add_argument(
            "--desativar-ausentes",
            action="store_true",
            help="Desativa (sem apagar) os objetivos que não estiverem no arquivo.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria feito sem gravar nada.",
        )

    def handle(self, *args, **options):
        cliente = self._obter_cliente(options["cliente"])
        caminho = Path(options["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        registros = self._ler(caminho)
        if not registros:
            raise CommandError("Nenhum objetivo reconhecido no arquivo.")

        criados = atualizados = 0
        codigos: list[str] = []

        with transaction.atomic():
            for registro in registros:
                codigos.append(registro["codigo"])
                objetivo = ObjetivoReferencial.raw_objects.filter(
                    is_deleted=False, cliente=cliente, codigo=registro["codigo"]
                ).first()
                acao = "atualizar"
                if objetivo is None:
                    objetivo = ObjetivoReferencial(cliente=cliente, codigo=registro["codigo"])
                    acao = "criar"
                objetivo.titulo = registro["titulo"]
                objetivo.texto = registro["texto"]
                objetivo.ordem = registro["ordem"]
                objetivo.ativo = True
                objetivo.full_clean()
                if options["dry_run"]:
                    self.stdout.write(f"[dry-run] {acao}: {registro['codigo']} — {registro['titulo']}")
                else:
                    objetivo.save()
                if acao == "criar":
                    criados += 1
                else:
                    atualizados += 1

            desativados = 0
            if options["desativar_ausentes"]:
                pendentes = (
                    ObjetivoReferencial.raw_objects.filter(
                        is_deleted=False, cliente=cliente, ativo=True
                    )
                    .exclude(codigo__in=codigos)
                )
                desativados = pendentes.count()
                if not options["dry_run"]:
                    pendentes.update(ativo=False)

            if options["dry_run"]:
                transaction.set_rollback(True)

        resumo = (
            f"{criados} objetivo(s) criado(s), {atualizados} atualizado(s)"
            + (f", {desativados} desativado(s)" if options["desativar_ausentes"] else "")
            + f" no município {cliente.nome}."
        )
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"[dry-run] {resumo} Nada foi gravado."))
        else:
            self.stdout.write(self.style.SUCCESS(resumo))

    # ------------------------------------------------------------------
    def _obter_cliente(self, referencia: str) -> Cliente:
        cliente = None
        if str(referencia).isdigit():
            cliente = Cliente.objects.filter(pk=int(referencia)).first()
        if cliente is None:
            cliente = Cliente.objects.filter(slug=referencia).first()
        if cliente is None:
            raise CommandError(f"Município não encontrado: {referencia}")
        return cliente

    def _ler(self, caminho: Path) -> list[dict]:
        bruto = caminho.read_text(encoding="utf-8-sig")
        if caminho.suffix.lower() == ".json" or bruto.lstrip()[:1] in "[{":
            carga = json.loads(bruto)
            if isinstance(carga, dict):
                carga = carga.get("objetivos") or []
            itens = [
                {
                    "codigo": str(item.get("codigo", "")).strip(),
                    "titulo": str(item.get("titulo", "")).strip(),
                    "texto": str(item.get("texto", "")).strip(),
                    "ordem": item.get("ordem"),
                }
                for item in carga
                if isinstance(item, dict)
            ]
        else:
            itens = []
            with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
                amostra = arquivo.read(1000)
                arquivo.seek(0)
                try:
                    dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t")
                except csv.Error:
                    dialeto = csv.excel
                    dialeto.delimiter = ";"
                for indice, linha in enumerate(csv.reader(arquivo, dialeto)):
                    if not linha or not any(campo.strip() for campo in linha):
                        continue
                    if indice == 0 and linha[0].strip().lower() in {"codigo", "código", "code"}:
                        continue
                    itens.append(
                        {
                            "codigo": linha[0].strip(),
                            "titulo": linha[1].strip() if len(linha) > 1 else "",
                            "texto": linha[2].strip() if len(linha) > 2 else "",
                            "ordem": linha[3].strip() if len(linha) > 3 else None,
                        }
                    )

        validos = []
        for posicao, item in enumerate(itens, start=1):
            if not item["codigo"] or not item["titulo"]:
                raise CommandError(
                    f"Linha {posicao}: informe código e título do objetivo."
                )
            try:
                item["ordem"] = int(item["ordem"]) if item["ordem"] not in (None, "") else posicao
            except (TypeError, ValueError):
                item["ordem"] = posicao
            validos.append(item)
        return validos
