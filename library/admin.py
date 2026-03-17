from django import forms
from django.contrib import admin

from core.admin_mixins import ClienteScopedAdminMixin
from meb.services import deliver_admin_broadcast

from .models import BlocoTexto, Midia


class MidiaAdminForm(forms.ModelForm):
    class Meta:
        model = Midia
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("titulo", "url", "gt"):
            if field in self.fields:
                self.fields[field].required = True


@admin.register(Midia)
class MidiaAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    form = MidiaAdminForm
    list_display = ("titulo", "url", "gt", "pergunta", "uploaded_by", "created_at")
    search_fields = ("titulo", "url", "descricao")
    list_filter = ("uploaded_by", "gt")

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        if not change and obj.gt_id and obj.cliente_id:
            titulo = obj.titulo or "Novo material"
            descricao = f" — {obj.descricao}" if obj.descricao else ""
            conteudo = f"Novo link na Biblioteca: {titulo}{descricao}\n{obj.url}"
            deliver_admin_broadcast(
                cliente_id=obj.cliente_id,
                autor=request.user,
                conteudo=conteudo,
                gt_ids=[obj.gt_id],
            )


@admin.register(BlocoTexto)
class BlocoTextoAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("titulo", "gt", "pergunta", "created_by", "updated_at")
    search_fields = ("titulo", "conteudo_html")
    list_filter = ("created_by", "gt")
