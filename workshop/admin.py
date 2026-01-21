"""Admin para quadros."""

from django.contrib import admin
from django.db import transaction

from .models import CelulaQuadro, Quadro, QuadroColuna, QuadroLinha


@admin.register(Quadro)
class QuadroAdmin(admin.ModelAdmin):
    list_display = ("gt", "template", "version", "updated_at")
    list_filter = ("template", "gt")
    change_form_template = "admin/workshop/quadro/change_form.html"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customiza o queryset para campos ForeignKey."""
        if db_field.name == "gt":
            from core.models import Usuario
            from curriculum.models import GT
            
            # Se o usuário é super admin, mostrar todos os GTs
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = GT.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = GT.objects.all()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        table_context = self._build_table_context(obj)
        context.update(table_context)
        return super().render_change_form(request, context, add, change, form_url, obj)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if request.method != "POST":
            return
        if not obj.pk:
            return
        self._save_table_data(request, obj)

    def _build_table_context(self, obj):
        if not obj:
            return {"show_quadro_table": False}

        linhas = list(QuadroLinha.objects.filter(quadro=obj).order_by("ordem", "linha"))
        colunas = list(QuadroColuna.objects.filter(quadro=obj).order_by("ordem", "coluna"))

        if not linhas:
            linhas = [
                QuadroLinha(quadro=obj, linha=linha, nome=f"Linha {linha}", ordem=idx)
                for idx, linha in enumerate(
                    CelulaQuadro.objects.filter(quadro=obj)
                    .values_list("linha", flat=True)
                    .distinct()
                    .order_by("linha")
                )
            ]
        if not colunas:
            colunas = [
                QuadroColuna(quadro=obj, coluna=coluna, nome=f"Coluna {coluna}", ordem=idx)
                for idx, coluna in enumerate(
                    CelulaQuadro.objects.filter(quadro=obj)
                    .values_list("coluna", flat=True)
                    .distinct()
                    .order_by("coluna")
                )
            ]

        celulas = {
            (celula.linha, celula.coluna): celula.valor_html
            for celula in CelulaQuadro.objects.filter(quadro=obj)
        }

        colunas_data = [
            {"coluna": coluna.coluna, "nome": coluna.nome, "ordem": coluna.ordem} for coluna in colunas
        ]
        linhas_data = []
        for linha in linhas:
            cells = []
            for coluna in colunas:
                cells.append(
                    {
                        "coluna": coluna.coluna,
                        "valor": celulas.get((linha.linha, coluna.coluna), ""),
                    }
                )
            linhas_data.append(
                {
                    "linha": linha.linha,
                    "nome": linha.nome,
                    "ordem": linha.ordem,
                    "cells": cells,
                }
            )

        return {
            "show_quadro_table": True,
            "quadro_linhas": linhas_data,
            "quadro_colunas": colunas_data,
        }

    def _save_table_data(self, request, obj):
        linhas = list(QuadroLinha.objects.filter(quadro=obj).order_by("ordem", "linha"))
        colunas = list(QuadroColuna.objects.filter(quadro=obj).order_by("ordem", "coluna"))

        if not linhas:
            linhas = [
                QuadroLinha.objects.get_or_create(
                    quadro=obj,
                    linha=linha,
                    defaults={"cliente": obj.cliente, "nome": f"Linha {linha}", "ordem": idx},
                )[0]
                for idx, linha in enumerate(
                    CelulaQuadro.objects.filter(quadro=obj)
                    .values_list("linha", flat=True)
                    .distinct()
                    .order_by("linha")
                )
            ]
        if not colunas:
            colunas = [
                QuadroColuna.objects.get_or_create(
                    quadro=obj,
                    coluna=coluna,
                    defaults={"cliente": obj.cliente, "nome": f"Coluna {coluna}", "ordem": idx},
                )[0]
                for idx, coluna in enumerate(
                    CelulaQuadro.objects.filter(quadro=obj)
                    .values_list("coluna", flat=True)
                    .distinct()
                    .order_by("coluna")
                )
            ]

        row_deletes = {
            linha.linha
            for linha in linhas
            if request.POST.get(f"row_delete_{linha.linha}") == "1"
        }
        if row_deletes:
            QuadroLinha.objects.filter(quadro=obj, linha__in=row_deletes).delete()
            CelulaQuadro.objects.filter(quadro=obj, linha__in=row_deletes).delete()
            linhas = [linha for linha in linhas if linha.linha not in row_deletes]

        col_deletes = {
            coluna.coluna
            for coluna in colunas
            if request.POST.get(f"col_delete_{coluna.coluna}") == "1"
        }
        if col_deletes:
            QuadroColuna.objects.filter(quadro=obj, coluna__in=col_deletes).delete()
            CelulaQuadro.objects.filter(quadro=obj, coluna__in=col_deletes).delete()
            colunas = [coluna for coluna in colunas if coluna.coluna not in col_deletes]

        for linha in linhas:
            updated_fields = []
            posted_name = request.POST.get(f"row_name_{linha.linha}")
            if posted_name is not None and posted_name.strip() and posted_name != linha.nome:
                linha.nome = posted_name.strip()
                updated_fields.append("nome")
            posted_order = request.POST.get(f"row_order_{linha.linha}")
            if posted_order is not None and posted_order.strip():
                try:
                    ordem = max(0, int(posted_order))
                except ValueError:
                    ordem = linha.ordem
                if ordem != linha.ordem:
                    linha.ordem = ordem
                    updated_fields.append("ordem")
            if updated_fields:
                linha.save(update_fields=[*updated_fields, "updated_at"])

        for coluna in colunas:
            updated_fields = []
            posted_name = request.POST.get(f"col_name_{coluna.coluna}")
            if posted_name is not None and posted_name.strip() and posted_name != coluna.nome:
                coluna.nome = posted_name.strip()
                updated_fields.append("nome")
            posted_order = request.POST.get(f"col_order_{coluna.coluna}")
            if posted_order is not None and posted_order.strip():
                try:
                    ordem = max(0, int(posted_order))
                except ValueError:
                    ordem = coluna.ordem
                if ordem != coluna.ordem:
                    coluna.ordem = ordem
                    updated_fields.append("ordem")
            if updated_fields:
                coluna.save(update_fields=[*updated_fields, "updated_at"])

        new_row_name = (request.POST.get("new_row_name") or "").strip()
        if new_row_name:
            next_linha = (max([linha.linha for linha in linhas], default=-1) + 1)
            next_ordem = (max([linha.ordem for linha in linhas], default=-1) + 1)
            QuadroLinha.objects.create(
                quadro=obj,
                linha=next_linha,
                nome=new_row_name,
                ordem=next_ordem,
                cliente=obj.cliente,
            )
            linhas.append(QuadroLinha(quadro=obj, linha=next_linha, nome=new_row_name, ordem=next_ordem))

        new_row_count = self._parse_int(request.POST.get("new_row_count"))
        if new_row_count and new_row_count > 0:
            prefix = request.POST.get("new_row_prefix")
            if prefix is None or prefix == "":
                prefix = "Linha "
            start = self._parse_int(request.POST.get("new_row_start"), default=1)
            next_linha = (max([linha.linha for linha in linhas], default=-1) + 1)
            next_ordem = (max([linha.ordem for linha in linhas], default=-1) + 1)
            for offset in range(new_row_count):
                nome = f"{prefix}{start + offset}"
                QuadroLinha.objects.create(
                    quadro=obj,
                    linha=next_linha + offset,
                    nome=nome,
                    ordem=next_ordem + offset,
                    cliente=obj.cliente,
                )
            linhas.extend(
                [
                    QuadroLinha(
                        quadro=obj,
                        linha=next_linha + offset,
                        nome=f"{prefix}{start + offset}",
                        ordem=next_ordem + offset,
                    )
                    for offset in range(new_row_count)
                ]
            )

        new_col_name = (request.POST.get("new_col_name") or "").strip()
        if new_col_name:
            next_coluna = (max([coluna.coluna for coluna in colunas], default=-1) + 1)
            next_ordem = (max([coluna.ordem for coluna in colunas], default=-1) + 1)
            QuadroColuna.objects.create(
                quadro=obj,
                coluna=next_coluna,
                nome=new_col_name,
                ordem=next_ordem,
                cliente=obj.cliente,
            )
            colunas.append(
                QuadroColuna(quadro=obj, coluna=next_coluna, nome=new_col_name, ordem=next_ordem)
            )

        new_col_count = self._parse_int(request.POST.get("new_col_count"))
        if new_col_count and new_col_count > 0:
            prefix = request.POST.get("new_col_prefix")
            if prefix is None or prefix == "":
                prefix = "Coluna "
            start = self._parse_int(request.POST.get("new_col_start"), default=1)
            next_coluna = (max([coluna.coluna for coluna in colunas], default=-1) + 1)
            next_ordem = (max([coluna.ordem for coluna in colunas], default=-1) + 1)
            for offset in range(new_col_count):
                nome = f"{prefix}{start + offset}"
                QuadroColuna.objects.create(
                    quadro=obj,
                    coluna=next_coluna + offset,
                    nome=nome,
                    ordem=next_ordem + offset,
                    cliente=obj.cliente,
                )
            colunas.extend(
                [
                    QuadroColuna(
                        quadro=obj,
                        coluna=next_coluna + offset,
                        nome=f"{prefix}{start + offset}",
                        ordem=next_ordem + offset,
                    )
                    for offset in range(new_col_count)
                ]
            )

        celulas_existentes = {
            (celula.linha, celula.coluna): celula
            for celula in CelulaQuadro.objects.filter(quadro=obj)
        }

        for linha in linhas:
            for coluna in colunas:
                key = f"cell_{linha.linha}_{coluna.coluna}"
                if key not in request.POST:
                    continue
                valor_html = request.POST.get(key, "")
                celula = celulas_existentes.get((linha.linha, coluna.coluna))
                if not celula and not valor_html:
                    continue
                if celula:
                    if celula.valor_html != valor_html:
                        celula.valor_html = valor_html
                        celula.save(update_fields=["valor_html", "updated_at"])
                else:
                    CelulaQuadro.objects.create(
                        quadro=obj,
                        linha=linha.linha,
                        coluna=coluna.coluna,
                        valor_html=valor_html,
                        cliente=obj.cliente,
                    )

    @staticmethod
    def _parse_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


@admin.register(CelulaQuadro)
class CelulaQuadroAdmin(admin.ModelAdmin):
    list_display = ("quadro", "linha", "coluna", "valor_html")
    list_filter = ("quadro",)


@admin.register(QuadroLinha)
class QuadroLinhaAdmin(admin.ModelAdmin):
    list_display = ("quadro", "linha", "ordem", "nome")
    list_filter = ("quadro",)


@admin.register(QuadroColuna)
class QuadroColunaAdmin(admin.ModelAdmin):
    list_display = ("quadro", "coluna", "ordem", "nome")
    list_filter = ("quadro",)
