"""
Comando de gerenciamento Django para carregar tags iniciais.
"""
import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from library.models import Tag
from core.models import Cliente


class Command(BaseCommand):
    """Comando para carregar tags iniciais no sistema."""
    
    help = 'Carrega tags iniciais no sistema de biblioteca de mídia'

    def handle(self, *args, **options):
        """Executa o comando de carregamento de tags."""
        fixture_path = os.path.join(
            settings.BASE_DIR, 
            'library', 
            'fixtures', 
            'initial_tags.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.ERROR(f'Arquivo de fixture não encontrado: {fixture_path}')
            )
            return
        
        # Busca o primeiro cliente disponível
        try:
            cliente = Cliente.objects.first()
            if not cliente:
                self.stdout.write(
                    self.style.ERROR('Nenhum cliente encontrado. Crie um cliente primeiro.')
                )
                return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao buscar cliente: {str(e)}')
            )
            return
        
        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                tags_data = json.load(f)
            
            created_count = 0
            updated_count = 0
            
            for tag_data in tags_data:
                fields = tag_data['fields']
                tag_id = tag_data['pk']
                
                tag, created = Tag.objects.update_or_create(
                    id=tag_id,
                    defaults={
                        'name': fields['name'],
                        'color': fields['color'],
                        'created_by': None,  # Tags do sistema não têm criador
                        'cliente': cliente
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Tag criada: {tag.name}')
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Tag atualizada: {tag.name}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processo concluído: {created_count} tags criadas, '
                    f'{updated_count} tags atualizadas'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao carregar tags: {str(e)}')
            )