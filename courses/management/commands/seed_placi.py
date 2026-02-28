from django.core.management.base import BaseCommand

from core.models import Cliente, Usuario
from courses.models import Curso, CursoItem, CursoModulo, PlanoAula, Rubrica, RubricaCriterio


class Command(BaseCommand):
    help = "Cria dados iniciais da PLACI para desenvolvimento local."

    def handle(self, *args, **options):
        cliente, _ = Cliente.objects.get_or_create(slug="placi-demo", defaults={"nome": "PLACI Demo", "ativo": True})
        admin, _ = Usuario.objects.get_or_create(
            email="admin.placi@demo.local",
            defaults={
                "nome": "Admin PLACI",
                "cliente": cliente,
                "role": Usuario.Role.ADMIN_CLIENTE,
                "is_staff": True,
            },
        )
        if not admin.has_usable_password():
            admin.set_password("admin123")
            admin.save(update_fields=["password"])

        curso, _ = Curso.objects.get_or_create(
            cliente=cliente,
            nome="Implementação do PPP na Prática Docente",
            defaults={
                "descricao": "Trilha formativa base da nova PLACI.",
                "categoria": Curso.Categoria.FORMACAO,
                "carga_horaria_total": 120,
                "carga_horaria_presencial": 40,
                "carga_horaria_sincrona": 20,
                "carga_horaria_plataforma": 60,
                "status": "publicado",
                "publicado": True,
            },
        )
        modulo, _ = CursoModulo.objects.get_or_create(
            cliente=cliente,
            curso=curso,
            ordem=1,
            tipo=CursoModulo.Tipo.MODULO,
            titulo="Módulo 1 - Diagnóstico e Planejamento",
            defaults={"descricao": "Fundamentos e planejamento institucional.", "carga_horaria": 20},
        )
        CursoItem.objects.get_or_create(
            cliente=cliente,
            modulo=modulo,
            ordem=1,
            tipo=CursoItem.Tipo.TEXTO,
            titulo="Guia de estudo inicial",
            defaults={"conteudo": "Leitura orientada sobre PPP.", "payload_json": {}},
        )
        plano, _ = PlanoAula.objects.get_or_create(
            cliente=cliente,
            curso=curso,
            autor=admin,
            escola="EMEF Modelo",
            componente_curricular="Língua Portuguesa",
            unidade_tematica="Leitura crítica",
            defaults={"status": PlanoAula.Status.RASCUNHO},
        )
        rubrica, _ = Rubrica.objects.get_or_create(
            cliente=cliente,
            curso=curso,
            nome="Rubrica base de avaliação formativa",
            defaults={"descricao": "Critérios para análise de plano de aula."},
        )
        RubricaCriterio.objects.get_or_create(
            cliente=cliente,
            rubrica=rubrica,
            nome="Clareza dos objetivos",
            defaults={"pontuacao_maxima": 10, "ordem": 1},
        )

        self.stdout.write(self.style.SUCCESS(f"Seed PLACI finalizado. Cliente={cliente.id}, Curso={curso.id}, Plano={plano.id}"))

