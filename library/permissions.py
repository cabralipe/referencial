"""Permissões customizadas para a biblioteca de mídia."""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import MediaFile, MediaFolder, FileShare, UserProfile


class IsOwnerOrPublic(permissions.BasePermission):
    """
    Permissão que permite acesso baseado no perfil do usuário e propriedade.
    - Admin: Acesso total a todos os arquivos
    - Editor: Pode criar, editar próprios arquivos e visualizar públicos/compartilhados
    - Viewer: Apenas visualizar arquivos públicos e compartilhados
    - Guest: Apenas arquivos públicos
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para acessar a view."""
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Super admin sempre tem acesso
        if getattr(request.user, 'role', None) == 'super_admin':
            return True
            
        # Para operações de escrita, verificar se o usuário pode criar/editar
        if request.method not in permissions.SAFE_METHODS:
            user_role = getattr(request.user, 'role', 'leitor')
            return user_role in ['super_admin', 'admin_cliente', 'articulador']
            
        return True
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica permissões específicas do objeto."""
        user = request.user
        user_role = getattr(user, 'role', 'leitor')
        
        # Super admin sempre tem acesso
        if user_role == 'super_admin':
            return True
            
        # Verificar se o usuário pertence ao mesmo cliente
        if hasattr(user, 'cliente_id') and hasattr(obj, 'cliente_id'):
            if user.cliente_id != obj.cliente_id:
                return False
        
        # Admin do cliente tem acesso total
        if user_role == 'admin_cliente':
            return True
            
        # Para operações de leitura
        if request.method in permissions.SAFE_METHODS:
            # Proprietário sempre pode ler
            if hasattr(obj, 'created_by') and obj.created_by == user:
                return True
            if hasattr(obj, 'owner') and obj.owner == user:
                return True
                
            # Arquivo público
            if hasattr(obj, 'is_public') and obj.is_public:
                return True
                
            # Arquivo compartilhado com o usuário
            if hasattr(obj, 'file_shares'):
                return obj.file_shares.filter(shared_with=user, is_active=True).exists()
                
            # Articuladores e membros GT podem ver arquivos do mesmo cliente
            if user_role in ['articulador', 'membro_gt']:
                return True
                
            return False
        
        # Para operações de escrita
        # Apenas proprietário ou admin pode editar/deletar
        if hasattr(obj, 'created_by') and obj.created_by == user:
            return True
        if hasattr(obj, 'owner') and obj.owner == user:
            return True
            
        # Articuladores podem editar arquivos do cliente
        if user_role == 'articulador':
            return True
            
        return False


class IsOwnerOrShared(permissions.BasePermission):
    """
    Permissão que permite acesso ao proprietário ou usuários com quem foi compartilhado.
    Para leitura: permite se for o proprietário ou se foi compartilhado com o usuário.
    Para escrita: depende do nível de permissão do compartilhamento.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para acessar a view."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica permissões específicas do objeto."""
        # Verificar se o usuário pertence ao mesmo cliente
        if not hasattr(request.user, 'cliente_id') or not hasattr(obj, 'cliente_id'):
            return False
            
        if request.user.cliente_id != obj.cliente_id:
            return False
        
        # Se for o proprietário, tem acesso total
        if obj.created_by == request.user:
            return True
        
        # Verificar se o arquivo foi compartilhado com o usuário
        if isinstance(obj, MediaFile):
            try:
                file_share = FileShare.objects.get(
                    file=obj,
                    shared_with=request.user
                )
                
                # Para operações de leitura
                if request.method in permissions.SAFE_METHODS:
                    return file_share.permission in ['read', 'write']
                
                # Para operações de escrita
                return file_share.permission == 'write'
                
            except FileShare.DoesNotExist:
                return False
        
        return False


class IsOwnerOrPublicFolder(permissions.BasePermission):
    """
    Permissão específica para pastas.
    Permite acesso se for o proprietário ou se a pasta for pública.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para acessar a view."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request: Request, view: APIView, obj: MediaFolder) -> bool:
        """Verifica permissões específicas da pasta."""
        # Verificar se o usuário pertence ao mesmo cliente
        if not hasattr(request.user, 'cliente_id') or not hasattr(obj, 'cliente_id'):
            return False
            
        if request.user.cliente_id != obj.cliente_id:
            return False
        
        # Para operações de leitura
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.created_by == request.user
        
        # Para operações de escrita, apenas o proprietário
        return obj.created_by == request.user


class CanManageShares(permissions.BasePermission):
    """
    Permissão para gerenciar compartilhamentos.
    Permite apenas ao proprietário do arquivo gerenciar compartilhamentos.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para acessar a view."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica permissões específicas do objeto."""
        # Para FileShare, verificar se é o proprietário do arquivo
        if isinstance(obj, FileShare):
            return (
                hasattr(request.user, 'cliente_id') and
                hasattr(obj.file, 'cliente_id') and
                request.user.cliente_id == obj.file.cliente_id and
                obj.file.created_by == request.user
            )
        
        # Para MediaFile, verificar se é o proprietário
        if isinstance(obj, MediaFile):
            return (
                hasattr(request.user, 'cliente_id') and
                hasattr(obj, 'cliente_id') and
                request.user.cliente_id == obj.cliente_id and
                obj.created_by == request.user
            )
        
        return False


class CanCreateInFolder(permissions.BasePermission):
    """
    Permissão para criar arquivos em uma pasta.
    Permite se a pasta for pública ou se o usuário for o proprietário.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para criar na pasta."""
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Verificar se foi especificada uma pasta
        folder_id = request.data.get('folder') or request.query_params.get('folder')
        if not folder_id:
            return True  # Pode criar na raiz
        
        try:
            folder = MediaFolder.objects.get(id=folder_id)
            
            # Verificar se o usuário pertence ao mesmo cliente
            if not hasattr(request.user, 'cliente_id') or not hasattr(folder, 'cliente_id'):
                return False
                
            if request.user.cliente_id != folder.cliente_id:
                return False
            
            # Permitir se a pasta for pública ou se for o proprietário
            return folder.is_public or folder.created_by == request.user
            
        except MediaFolder.DoesNotExist:
            return False


class IsOwnerOrReadOnlyPublic(permissions.BasePermission):
    """
    Permissão que permite leitura para itens públicos e acesso total para proprietários.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para acessar a view."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica permissões específicas do objeto."""
        # Verificar se o usuário pertence ao mesmo cliente
        if not hasattr(request.user, 'cliente_id') or not hasattr(obj, 'cliente_id'):
            return False
            
        if request.user.cliente_id != obj.cliente_id:
            return False
        
        # Se for o proprietário, tem acesso total
        if obj.created_by == request.user:
            return True
        
        # Para operações de leitura em itens públicos
        if request.method in permissions.SAFE_METHODS and obj.is_public:
            return True
        
        return False


class CanAccessFileVersions(permissions.BasePermission):
    """
    Permissão para acessar versões de arquivos.
    Permite se o usuário tem acesso ao arquivo principal.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para acessar a view."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica permissões específicas da versão do arquivo."""
        # Verificar permissões no arquivo principal
        file_permission = IsOwnerOrShared()
        return file_permission.has_object_permission(request, view, obj.file)


class CanManageTags(permissions.BasePermission):
    """
    Permissão para gerenciar tags baseada no perfil do usuário.
    - Admin/Super Admin: Pode criar, editar e deletar todas as tags
    - Articulador: Pode criar e editar tags do cliente
    - Outros: Apenas visualizar tags
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica se o usuário tem permissão para gerenciar tags."""
        if not request.user or not request.user.is_authenticated:
            return False
            
        user_role = getattr(request.user, 'role', 'leitor')
        
        # Super admin sempre tem acesso
        if user_role == 'super_admin':
            return True
            
        # Para operações de escrita, verificar permissões
        if request.method not in permissions.SAFE_METHODS:
            return user_role in ['super_admin', 'admin_cliente', 'articulador']
            
        return True
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica se o usuário pode gerenciar a tag específica."""
        user = request.user
        user_role = getattr(user, 'role', 'leitor')
        
        # Super admin sempre tem acesso
        if user_role == 'super_admin':
            return True
            
        # Verificar se o usuário pertence ao mesmo cliente
        if hasattr(user, 'cliente_id') and hasattr(obj, 'cliente_id'):
            if user.cliente_id != obj.cliente_id:
                return False
        
        # Admin do cliente pode gerenciar todas as tags
        if user_role == 'admin_cliente':
            return True
            
        # Para leitura, todos os usuários autenticados podem ver
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Para escrita, apenas articuladores e acima
        return user_role in ['articulador', 'admin_cliente', 'super_admin']


class MediaLibraryPermission(permissions.BasePermission):
    """
    Permissão baseada no sistema de perfis da Media Library.
    Usa o UserProfile para determinar permissões específicas.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Verifica permissões gerais baseadas no perfil do usuário."""
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Obter ou criar perfil do usuário
        profile = UserProfile.get_or_create_for_user(request.user)
        
        # Mapear ações da view para permissões
        action = getattr(view, 'action', None)
        
        if action == 'create':
            return profile.can_perform_action('upload')
        elif action in ['update', 'partial_update']:
            return True  # Verificação específica no has_object_permission
        elif action == 'destroy':
            return True  # Verificação específica no has_object_permission
        elif action in ['list', 'retrieve']:
            return True  # Todos podem listar/ver (filtrado no queryset)
            
        # Para ações customizadas, verificar método HTTP
        if request.method not in permissions.SAFE_METHODS:
            effective_role = profile.get_effective_media_role()
            return effective_role in [UserProfile.MediaRole.EDITOR, UserProfile.MediaRole.ADMIN]
            
        return True
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Verifica permissões específicas do objeto."""
        if not request.user or not request.user.is_authenticated:
            return False
            
        profile = UserProfile.get_or_create_for_user(request.user)
        effective_role = profile.get_effective_media_role()
        
        # Admin sempre tem acesso
        if effective_role == UserProfile.MediaRole.ADMIN:
            return True
            
        # Verificar cliente
        if hasattr(request.user, 'cliente_id') and hasattr(obj, 'cliente_id'):
            if request.user.cliente_id != obj.cliente_id:
                return False
        
        # Para leitura
        if request.method in permissions.SAFE_METHODS:
            # Proprietário sempre pode ler
            if hasattr(obj, 'owner') and obj.owner == request.user:
                return True
            if hasattr(obj, 'created_by') and obj.created_by == request.user:
                return True
                
            # Arquivo público
            if hasattr(obj, 'is_public') and obj.is_public:
                return profile.can_perform_action('view_public')
                
            # Arquivo compartilhado
            if hasattr(obj, 'file_shares'):
                shared = obj.file_shares.filter(shared_with=request.user, is_active=True).exists()
                if shared:
                    return profile.can_perform_action('view_shared')
                    
            # Viewers e acima podem ver arquivos do mesmo cliente
            return effective_role in [UserProfile.MediaRole.VIEWER, UserProfile.MediaRole.EDITOR, UserProfile.MediaRole.ADMIN]
        
        # Para escrita
        action = getattr(view, 'action', None)
        
        # Verificar se é proprietário
        is_owner = False
        if hasattr(obj, 'owner') and obj.owner == request.user:
            is_owner = True
        elif hasattr(obj, 'created_by') and obj.created_by == request.user:
            is_owner = True
            
        if action == 'destroy':
            if is_owner:
                return profile.can_perform_action('delete_own')
            else:
                return profile.can_perform_action('delete_others')
        elif action in ['update', 'partial_update']:
            # Proprietário pode editar se tiver permissão
            if is_owner:
                return effective_role in [UserProfile.MediaRole.EDITOR, UserProfile.MediaRole.ADMIN]
            # Outros só se for admin
            return effective_role == UserProfile.MediaRole.ADMIN
            
        # Para outras operações de escrita, verificar se é editor ou admin
        return effective_role in [UserProfile.MediaRole.EDITOR, UserProfile.MediaRole.ADMIN]