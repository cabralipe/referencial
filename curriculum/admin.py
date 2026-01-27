"""Admin do domínio de currículo."""

import re
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.utils.html import strip_tags

from .models import Area, Anexo, GT, Pergunta, Resposta, Tarefa, TextoUnico
from meb.services import deliver_admin_broadcast


class BroadcastMessageForm(ActionForm):
    conteudo = forms.CharField(
        label="Mensagem para o chat",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Digite a mensagem do disparo..."}),
    )


class BasicRichTextWidget(forms.Textarea):
    template_name = "admin/widgets/basic_rich_text.html"


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = "__all__"
        widgets = {
            "descricao_html": BasicRichTextWidget(attrs={"rows": 6}),
        }

    def clean_descricao_html(self):
        conteudo = self.cleaned_data.get("descricao_html", "")
        if not conteudo:
            return conteudo
        return re.sub(r"<script[\s\S]*?</script>", "", conteudo, flags=re.IGNORECASE)


@admin.register(GT)
class GTAdmin(admin.ModelAdmin):
    list_display = ("nome", "etapa", "cliente", "created_at")
    search_fields = ("nome", "etapa", "cliente__nome")
    filter_horizontal = ("membros",)
    list_filter = ("cliente", "etapa")
    action_form = BroadcastMessageForm
    actions = ["broadcast_chat_message"]
    
    def get_queryset(self, request):
        """Super admins podem ver todos os GTs, outros usuários seguem o filtro normal."""
        from core.models import Usuario
        
        # Se o usuário é super admin, usar raw_objects para ver todos os GTs
        if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
            return GT.raw_objects.filter(is_deleted=False)
        
        # Para outros usuários, usar o queryset padrão (com filtro de cliente)
        return super().get_queryset(request)

    @admin.action(description="Disparar mensagem no chat para os GTs selecionados")
    def broadcast_chat_message(self, request, queryset):
        from core.models import Usuario

        user_role = getattr(request.user, "role", None)
        if user_role not in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}:
            self.message_user(
                request,
                "Apenas administradores podem enviar disparos de mensagens.",
                level=messages.ERROR,
            )
            return

        conteudo = (request.POST.get("conteudo") or "").strip()
        if not conteudo:
            self.message_user(
                request,
                "Digite a mensagem antes de enviar o disparo.",
                level=messages.ERROR,
            )
            return

        total_enviados = 0
        skipped = 0
        gts_by_cliente: dict[int, list[int]] = {}
        for gt in queryset:
            if not gt.cliente_id:
                skipped += 1
                continue
            gts_by_cliente.setdefault(gt.cliente_id, []).append(gt.id)

        for cliente_id, gt_ids in gts_by_cliente.items():
            enviados = deliver_admin_broadcast(
                cliente_id=cliente_id,
                autor=request.user,
                conteudo=conteudo,
                gt_ids=gt_ids,
                include_all=False,
            )
            total_enviados += enviados

        if total_enviados == 0:
            self.message_user(
                request,
                "Nenhum destinatário elegível encontrado para este disparo.",
                level=messages.WARNING,
            )
            return

        msg = f"Disparo enviado para {total_enviados} destinatário(s)."
        if skipped:
            msg += f" {skipped} GT(s) sem cliente foram ignorados."
        self.message_user(request, msg, level=messages.SUCCESS)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    form = AreaForm
    list_display = ("nome", "cliente", "created_at")
    search_fields = ("nome", "cliente__nome")
    list_filter = ("cliente",)
    filter_horizontal = ("gts",)
    fields = ("nome", "cliente", "gts", "descricao_html")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "gts":
            from core.models import Usuario

            if hasattr(request.user, "role") and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = GT.raw_objects.filter(is_deleted=False)
            else:
                kwargs["queryset"] = GT.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


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
    list_display = ("nome", "ordem", "tipo", "status", "cliente", "id")
    list_filter = ("cliente", "tipo", "status")
    search_fields = ("nome", "cliente__nome")
    fields = ("nome", "cliente", "ordem", "etapa", "tipo", "status")
    
    def get_queryset(self, request):
        """Customiza o queryset para super admins verem todas as tarefas."""
        from core.models import Usuario
        
        # Se o usuário é super admin, mostrar todas as tarefas
        if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
            return Tarefa.raw_objects.filter(is_deleted=False)
        
        # Para outros usuários, usar o queryset padrão (com filtro de cliente)
        return super().get_queryset(request)
    
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
        """Customiza o queryset para campos ManyToMany."""
        if db_field.name == "gts":
            from core.models import Usuario
            from django.db.models import Q
            
            # Se o usuário é super admin, mostrar todos os GTs
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = GT.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                base_queryset = GT.objects.all()
                
                # Se estamos editando uma pergunta existente, incluir os GTs já associados
                # mesmo que eles não estejam normalmente disponíveis para o usuário
                pergunta_id = self._get_pergunta_id_from_request(request)
                if pergunta_id:
                    try:
                        pergunta = Pergunta.raw_objects.get(id=pergunta_id)
                        gts_salvos_ids = list(pergunta.gts.values_list('id', flat=True))
                        
                        if gts_salvos_ids:
                            # Combinar GTs disponíveis com GTs já salvos usando Q objects
                            kwargs["queryset"] = GT.raw_objects.filter(
                                Q(id__in=base_queryset.values_list('id', flat=True)) |
                                Q(id__in=gts_salvos_ids, is_deleted=False)
                            ).distinct()
                        else:
                            kwargs["queryset"] = base_queryset
                    except (ValueError, Pergunta.DoesNotExist):
                        kwargs["queryset"] = base_queryset
                else:
                    kwargs["queryset"] = base_queryset
        
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def _get_pergunta_id_from_request(self, request):
        """Extrai o ID da pergunta da URL de edição."""
        try:
            # Verificar se é uma URL de edição
            if hasattr(request, 'path') and '/change/' in request.path:
                url_parts = request.path.split('/')
                # Procurar por padrão: .../pergunta/{id}/change/
                for i, part in enumerate(url_parts):
                    if part == 'pergunta' and i + 1 < len(url_parts):
                        return int(url_parts[i + 1])
        except (ValueError, IndexError):
            pass
        return None
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customiza o queryset para campos ForeignKey."""
        if db_field.name == "tarefa":
            from core.models import Usuario
            
            # Se o usuário é super admin, mostrar todas as tarefas
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = Tarefa.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = Tarefa.objects.all()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """Garante que o cliente_id seja definido corretamente baseado na tarefa."""
        # Se não há cliente_id definido, usar o cliente da tarefa
        if not obj.cliente_id and obj.tarefa:
            obj.cliente_id = obj.tarefa.cliente_id
        
        super().save_model(request, obj, form, change)


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
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customiza o queryset para campos ForeignKey."""
        if db_field.name == "gt":
            from core.models import Usuario
            
            # Se o usuário é super admin, mostrar todos os GTs
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = GT.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = GT.objects.all()
        elif db_field.name == "pergunta":
            from core.models import Usuario
            
            # Se o usuário é super admin, mostrar todas as perguntas
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = Pergunta.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = Pergunta.objects.all()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ("resposta", "url", "ordem")
    list_filter = ("resposta",)


@admin.register(TextoUnico)
class TextoUnicoAdmin(admin.ModelAdmin):
    list_display = ("gt", "tarefa", "responsavel", "version", "updated_at")
    list_filter = ("gt", "tarefa")
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customiza o queryset para campos ForeignKey."""
        if db_field.name == "tarefa":
            from core.models import Usuario
            
            # Se o usuário é super admin, mostrar todas as tarefas
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = Tarefa.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = Tarefa.objects.all()
        elif db_field.name == "gt":
            from core.models import Usuario
            
            # Se o usuário é super admin, mostrar todos os GTs
            if hasattr(request.user, 'role') and request.user.role == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = GT.raw_objects.filter(is_deleted=False)
            # Para outros usuários, usar o queryset padrão (com filtro de cliente)
            else:
                kwargs["queryset"] = GT.objects.all()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
