"""Admin do domínio de currículo."""

import re
from django import forms
from django.contrib import admin
from django.utils.html import strip_tags

from .models import Anexo, GT, Pergunta, Resposta, Tarefa, TextoUnico


@admin.register(GT)
class GTAdmin(admin.ModelAdmin):
    list_display = ("nome", "etapa", "cliente", "created_at")
    search_fields = ("nome", "etapa", "cliente__nome")
    filter_horizontal = ("membros",)
    list_filter = ("cliente", "etapa")
    
    def get_queryset(self, request):
        """Super admins podem ver todos os GTs, outros usuários seguem o filtro normal."""
        from core.models import Usuario
        
        # Se o usuário é super admin, usar raw_objects para ver todos os GTs
        if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
            return GT.raw_objects.filter(is_deleted=False)
        
        # Para outros usuários, usar o queryset padrão (com filtro de cliente)
        return super().get_queryset(request)


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get('cliente')
        ordem = cleaned_data.get('ordem')
        tipo = cleaned_data.get('tipo')
        
        if cliente and ordem and tipo:
            # Verificar se já existe uma tarefa com a mesma combinação
            existing_tarefa = Tarefa.objects.filter(
                cliente=cliente,
                ordem=ordem,
                tipo=tipo
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_tarefa.exists():
                existing = existing_tarefa.first()
                raise forms.ValidationError(
                    f"Já existe uma tarefa com Cliente '{cliente.nome}', "
                    f"Ordem {ordem} e Tipo '{tipo}' (ID: {existing.id}). "
                    f"Por favor, escolha uma ordem diferente ou modifique a tarefa existente."
                )
        
        return cleaned_data


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    form = TarefaForm
    list_display = ("ordem", "tipo", "status", "cliente", "id")
    list_filter = ("cliente", "tipo", "status")
    search_fields = ("cliente__nome",)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Adicionar informações úteis no help_text
        if 'ordem' in form.base_fields:
            if obj and obj.cliente:
                # Mostrar tarefas existentes para o cliente
                existing_tasks = Tarefa.objects.filter(cliente=obj.cliente).order_by('ordem', 'tipo')
                if existing_tasks.exists():
                    tasks_info = []
                    for task in existing_tasks:
                        if task.pk != (obj.pk if obj else None):
                            tasks_info.append(f"Ordem {task.ordem} - {task.tipo}")
                    
                    if tasks_info:
                        form.base_fields['ordem'].help_text = (
                            f"Tarefas existentes para {obj.cliente.nome}: " + 
                            ", ".join(tasks_info[:5]) + 
                            ("..." if len(tasks_info) > 5 else "")
                        )
            else:
                form.base_fields['ordem'].help_text = "Selecione um cliente primeiro para ver as tarefas existentes."
        
        return form


@admin.register(Pergunta)
class PerguntaAdmin(admin.ModelAdmin):
    list_display = ("tarefa", "ordem", "obrigatoria", "permite_upload")
    list_filter = ("tarefa", "permite_upload", "obrigatoria")
    search_fields = ("texto",)
    filter_horizontal = ("gts",)
    fields = ("tarefa", "ordem", "texto", "permite_upload", "obrigatoria", "gts")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "gts":
            try:
                # Detecta change view e carrega a Pergunta sem escopo de cliente
                object_id = request.resolver_match.kwargs.get("object_id")
            except Exception:
                object_id = None
            if object_id:
                try:
                    pergunta = Pergunta.raw_objects.get(pk=object_id)
                    kwargs["queryset"] = GT.raw_objects.filter(cliente_id=pergunta.cliente_id)
                except Pergunta.DoesNotExist:
                    # fallback: mantém escopo atual
                    kwargs["queryset"] = GT.objects.all()
            else:
                # add view: usa o escopo padrão (cliente atual)
                kwargs["queryset"] = GT.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Customiza o queryset para campos ManyToMany."""
        if db_field.name == "gts":
            from core.models import Usuario
            
            # Se o usuário é super admin, mostrar todos os GTs
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = GT.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = GT.objects.all()
        
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class RespostaForm(forms.ModelForm):
    class Meta:
        model = Resposta
        fields = '__all__'
        widgets = {
            'conteudo_html': forms.Textarea(attrs={
                'rows': 6,
                'cols': 80,
                'placeholder': 'Digite o conteúdo da resposta em texto simples...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se há uma instância existente, converte HTML para texto simples
        if self.instance and self.instance.pk and self.instance.conteudo_html:
            # Remove tags HTML e limpa espaços extras
            plain_text = strip_tags(self.instance.conteudo_html)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            self.initial['conteudo_html'] = plain_text
    
    def clean_conteudo_html(self):
        """Garante que o conteúdo seja salvo como texto simples."""
        conteudo = self.cleaned_data.get('conteudo_html', '')
        if conteudo:
            # Remove qualquer tag HTML que possa ter sido inserida
            plain_text = strip_tags(conteudo)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            return plain_text
        return conteudo


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
    form = RespostaForm
    list_display = ("gt", "pergunta", "autor", "version", "updated_at")
    list_filter = ("gt", "pergunta", "autor")
    search_fields = ("conteudo_html",)
    fieldsets = (
        (None, {
            'fields': ('gt', 'pergunta', 'conteudo_html', 'autor')
        }),
        ('Informações do Sistema', {
            'fields': ('version',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('version',)


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ("resposta", "url", "ordem")
    list_filter = ("resposta",)


@admin.register(TextoUnico)
class TextoUnicoAdmin(admin.ModelAdmin):
    list_display = ("gt", "tarefa", "responsavel", "version", "updated_at")
    list_filter = ("gt", "tarefa")
