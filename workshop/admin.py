"""Admin para quadros."""

from django.contrib import admin

from .models import CelulaQuadro, Quadro


class CelulaQuadroInline(admin.TabularInline):
    model = CelulaQuadro
    extra = 0


@admin.register(Quadro)
class QuadroAdmin(admin.ModelAdmin):
    list_display = ("gt", "template", "version", "updated_at")
    list_filter = ("template", "gt")
    inlines = [CelulaQuadroInline]
    
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


@admin.register(CelulaQuadro)
class CelulaQuadroAdmin(admin.ModelAdmin):
    list_display = ("quadro", "linha", "coluna", "valor_html")
    list_filter = ("quadro",)
