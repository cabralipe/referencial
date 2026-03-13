from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0012_usuario_escola_and_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TrilhaFormativa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("nome", models.CharField(max_length=255, verbose_name="Nome")),
                ("descricao", models.TextField(blank=True, verbose_name="Descri\u00e7\u00e3o")),
                ("capa", models.ImageField(blank=True, null=True, upload_to="ava/trilhas/capas/", verbose_name="Capa")),
                ("ordem_exibicao", models.PositiveIntegerField(default=0, verbose_name="Ordem de exibi\u00e7\u00e3o")),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
                (
                    "carga_horaria_total",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Calculada automaticamente ou definida manualmente.",
                        verbose_name="Carga hor\u00e1ria total",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trilha Formativa",
                "verbose_name_plural": "Trilhas Formativas",
                "ordering": ("ordem_exibicao", "nome"),
            },
        ),
        migrations.CreateModel(
            name="CursoCategoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("nome", models.CharField(max_length=150, verbose_name="Nome")),
                ("descricao", models.TextField(blank=True, verbose_name="Descri\u00e7\u00e3o")),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Categoria de Curso",
                "verbose_name_plural": "Categorias de Curso",
                "ordering": ("nome",),
            },
        ),
        migrations.CreateModel(
            name="Curso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("titulo", models.CharField(max_length=255, verbose_name="T\u00edtulo")),
                ("slug", models.SlugField(max_length=255, unique=True, verbose_name="Slug")),
                ("descricao_curta", models.CharField(blank=True, max_length=255, verbose_name="Descri\u00e7\u00e3o curta")),
                ("descricao_longa", models.TextField(blank=True, verbose_name="Descri\u00e7\u00e3o longa")),
                ("capa", models.ImageField(blank=True, null=True, upload_to="ava/cursos/capas/", verbose_name="Capa")),
                ("carga_horaria", models.PositiveIntegerField(default=0, verbose_name="Carga Hor\u00e1ria")),
                ("nivel", models.CharField(blank=True, max_length=100, verbose_name="N\u00edvel")),
                ("publico_alvo", models.CharField(blank=True, max_length=255, verbose_name="P\u00fablico-alvo")),
                ("ementa", models.TextField(blank=True, verbose_name="Ementa")),
                ("objetivos", models.TextField(blank=True, verbose_name="Objetivos")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("rascunho", "Rascunho"),
                            ("publicado", "Publicado"),
                            ("arquivado", "Arquivado"),
                        ],
                        default="rascunho",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "is_aberto",
                    models.BooleanField(default=False, verbose_name="Curso aberto (Inscri\u00e7\u00e3o livre)?"),
                ),
                ("permite_certificado", models.BooleanField(default=True, verbose_name="Permite certificado?")),
                (
                    "nota_minima",
                    models.DecimalField(
                        decimal_places=2,
                        default=70.0,
                        max_digits=5,
                        verbose_name="Nota m\u00ednima para aprova\u00e7\u00e3o",
                    ),
                ),
                (
                    "progresso_minimo",
                    models.PositiveIntegerField(
                        default=100,
                        help_text="Percentual m\u00ednimo de conclus\u00e3o exigido.",
                        verbose_name="Progresso m\u00ednimo (%)",
                    ),
                ),
                (
                    "data_inicio_disponibilidade",
                    models.DateTimeField(blank=True, null=True, verbose_name="In\u00edcio da disponibilidade"),
                ),
                (
                    "data_fim_disponibilidade",
                    models.DateTimeField(blank=True, null=True, verbose_name="Fim da disponibilidade"),
                ),
                ("ordem_na_trilha", models.PositiveIntegerField(default=0, verbose_name="Ordem dentro da trilha principal")),
                (
                    "autor_principal",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cursos_criados",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Autor/Respons\u00e1vel",
                    ),
                ),
                (
                    "categoria",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cursos",
                        to="ava.cursocategoria",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ava_cursos",
                        to="core.cliente",
                    ),
                ),
                (
                    "trilhas",
                    models.ManyToManyField(blank=True, related_name="cursos", to="ava.trilhaformativa"),
                ),
            ],
            options={
                "verbose_name": "Curso",
                "verbose_name_plural": "Cursos",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="CursoModulo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("titulo", models.CharField(max_length=255, verbose_name="T\u00edtulo")),
                ("descricao", models.TextField(blank=True, verbose_name="Descri\u00e7\u00e3o")),
                ("ordem", models.PositiveIntegerField(default=0, verbose_name="Ordem")),
                ("is_active", models.BooleanField(default=True, verbose_name="P\u00fablico/Dispon\u00edvel?")),
                (
                    "data_liberacao_programada",
                    models.DateTimeField(blank=True, null=True, verbose_name="Data de libera\u00e7\u00e3o programada"),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ava_cursomodulos",
                        to="core.cliente",
                    ),
                ),
                (
                    "curso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modulos",
                        to="ava.curso",
                    ),
                ),
                (
                    "pre_requisito_modulo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="modulos_dependentes",
                        to="ava.cursomodulo",
                        verbose_name="M\u00f3dulo Pr\u00e9-requisito",
                    ),
                ),
            ],
            options={
                "verbose_name": "M\u00f3dulo",
                "verbose_name_plural": "M\u00f3dulos",
                "ordering": ("curso", "ordem"),
                "unique_together": {("curso", "ordem")},
            },
        ),
        migrations.CreateModel(
            name="Aula",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("titulo", models.CharField(max_length=255, verbose_name="T\u00edtulo")),
                ("resumo", models.TextField(blank=True, verbose_name="Resumo")),
                ("ordem", models.PositiveIntegerField(default=0, verbose_name="Ordem")),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("conteudo", "Conte\u00fado Te\u00f3rico"),
                            ("mista", "Teoria + Pr\u00e1tica"),
                            ("avaliativa", "Avalia\u00e7\u00e3o/Quiz"),
                        ],
                        default="conteudo",
                        max_length=20,
                        verbose_name="Tipo",
                    ),
                ),
                ("duracao_estimada_minutos", models.PositiveIntegerField(default=0, verbose_name="Dura\u00e7\u00e3o (Min)")),
                ("is_obigatoria", models.BooleanField(default=True, verbose_name="Obrigat\u00f3ria?")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aula Publicada?")),
                ("data_liberacao", models.DateTimeField(blank=True, null=True, verbose_name="Data de libera\u00e7\u00e3o")),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "modulo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aulas",
                        to="ava.cursomodulo",
                    ),
                ),
                (
                    "pre_requisito_aula",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="aulas_dependentes",
                        to="ava.aula",
                    ),
                ),
            ],
            options={
                "verbose_name": "Aula",
                "verbose_name_plural": "Aulas",
                "ordering": ("modulo", "ordem"),
            },
        ),
        migrations.CreateModel(
            name="ConteudoAula",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("texto", "Texto Rico"),
                            ("video", "V\u00eddeo Incorporado"),
                            ("pdf", "PDF/Apostila"),
                            ("arquivo", "Arquivo para Download"),
                            ("link", "Link Externo"),
                            ("apresentacao", "Apresenta\u00e7\u00e3o Interativa"),
                            ("imagem", "Imagem"),
                            ("audio", "\u00c1udio/Podcast"),
                            ("embed", "Embed HTML Gen\u00e9rico"),
                        ],
                        max_length=30,
                        verbose_name="Tipo",
                    ),
                ),
                ("titulo", models.CharField(max_length=255, verbose_name="T\u00edtulo/R\u00f3tulo")),
                ("descricao", models.TextField(blank=True, verbose_name="Descri\u00e7\u00e3o Menor")),
                ("ordem", models.PositiveIntegerField(default=0, verbose_name="Ordem")),
                ("is_obrigatorio", models.BooleanField(default=True, verbose_name="Consumo Obrigat\u00f3rio?")),
                ("conteudo_texto", models.TextField(blank=True, verbose_name="Texto Rico")),
                ("url", models.URLField(blank=True, max_length=1000, verbose_name="URL de V\u00eddeo/Link/Embed")),
                (
                    "arquivo",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="ava/aulas/arquivos/",
                        verbose_name="Arquivo/PDF/M\u00eddia",
                    ),
                ),
                ("embed_code", models.TextField(blank=True, verbose_name="C\u00f3digo de Embed (Iframe, etc)")),
                (
                    "aula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conteudos",
                        to="ava.aula",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Conte\u00fado de Aula",
                "verbose_name_plural": "Conte\u00fados de Aula",
                "ordering": ("aula", "ordem"),
            },
        ),
        migrations.CreateModel(
            name="Atividade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("quiz", "Quiz Objetivo"),
                            ("tarefa", "Tarefa Discursiva"),
                            ("envio_arquivo", "Envio de Arquivo"),
                            ("questionario", "Question\u00e1rio Simples (Pesquisa)"),
                            ("reflexao", "Reflex\u00e3o Guiada"),
                        ],
                        max_length=30,
                        verbose_name="Tipo da Atividade",
                    ),
                ),
                ("titulo", models.CharField(max_length=255, verbose_name="T\u00edtulo")),
                ("descricao", models.TextField(blank=True, verbose_name="Descri\u00e7\u00e3o/Enunciado")),
                ("instrucoes", models.TextField(blank=True, verbose_name="Instru\u00e7\u00f5es de envio")),
                ("nota_maxima", models.DecimalField(decimal_places=2, default=100.0, max_digits=5, verbose_name="Nota M\u00e1xima")),
                ("peso", models.DecimalField(decimal_places=2, default=1.0, max_digits=5, verbose_name="Peso na composi\u00e7\u00e3o da m\u00e9dia")),
                ("is_obrigatoria", models.BooleanField(default=True, verbose_name="Atividade Obrigat\u00f3ria?")),
                ("prazo_envio", models.DateTimeField(blank=True, null=True, verbose_name="Prazo fatal (Opcional)")),
                (
                    "tentativas_permitidas",
                    models.PositiveIntegerField(default=1, help_text="0 para ilimitadas", verbose_name="M\u00e1ximo de Tentativas"),
                ),
                (
                    "correcao_automatica",
                    models.BooleanField(
                        default=False,
                        help_text="V\u00e1lido para Quizzes e Question\u00e1rios",
                        verbose_name="Corre\u00e7\u00e3o Autom\u00e1tica?",
                    ),
                ),
                (
                    "criterio_aprovacao",
                    models.DecimalField(
                        decimal_places=2,
                        default=70.0,
                        max_digits=5,
                        verbose_name="Nota m\u00ednima (se aplic\u00e1vel)",
                    ),
                ),
                (
                    "aula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="atividades",
                        to="ava.aula",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Atividade",
                "verbose_name_plural": "Atividades",
                "ordering": ("aula",),
            },
        ),
        migrations.CreateModel(
            name="QuizQuestao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("enunciado", models.TextField(verbose_name="Enunciado da Quest\u00e3o")),
                ("peso", models.DecimalField(decimal_places=2, default=1.0, max_digits=5, verbose_name="Peso da Quest\u00e3o")),
                ("ordem", models.PositiveIntegerField(default=0, verbose_name="Ordem Exibi\u00e7\u00e3o")),
                ("feedback_acerto", models.TextField(blank=True, verbose_name="Feedback (Acerto)")),
                ("feedback_erro", models.TextField(blank=True, verbose_name="Feedback (Erro)")),
                (
                    "atividade",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questoes",
                        to="ava.atividade",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Quest\u00e3o de Quiz",
                "verbose_name_plural": "Quest\u00f5es de Quiz",
                "ordering": ("ordem",),
            },
        ),
        migrations.CreateModel(
            name="QuizAlternativa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("texto", models.TextField(verbose_name="Texto da Alternativa")),
                ("is_correta", models.BooleanField(default=False, verbose_name="Alternativa Correta?")),
                ("ordem", models.PositiveIntegerField(default=0, verbose_name="Ordem")),
                ("feedback_especifico", models.TextField(blank=True, verbose_name="Feedback Espec\u00edfico")),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "questao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alternativas",
                        to="ava.quizquestao",
                    ),
                ),
            ],
            options={"ordering": ("ordem",)},
        ),
        migrations.CreateModel(
            name="MatriculaCurso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ativa", "Ativa"),
                            ("suspensa", "Suspensa"),
                            ("concluida", "Conclu\u00edda"),
                            ("cancelada", "Cancelada"),
                        ],
                        default="ativa",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                ("data_matricula", models.DateTimeField(auto_now_add=True, verbose_name="Data da Matr\u00edcula")),
                ("data_conclusao", models.DateTimeField(blank=True, null=True, verbose_name="Data de Conclus\u00e3o")),
                ("progresso_percentual", models.PositiveIntegerField(default=0, verbose_name="Progresso Total (%)")),
                ("nota_final_obtida", models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name="Nota Final")),
                (
                    "aluno",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cursos_matriculados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "curso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matriculas",
                        to="ava.curso",
                    ),
                ),
                (
                    "matriculado_por",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="matriculas_realizadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Matr\u00edcula no Curso",
                "verbose_name_plural": "Matr\u00edculas nos Cursos",
                "unique_together": {("curso", "aluno")},
            },
        ),
        migrations.CreateModel(
            name="MatriculaTrilha",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("ativa", "Ativa"), ("concluida", "Conclu\u00edda")],
                        default="ativa",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                ("data_matricula", models.DateTimeField(auto_now_add=True, verbose_name="Data da Matr\u00edcula")),
                ("data_conclusao", models.DateTimeField(blank=True, null=True, verbose_name="Data de Conclus\u00e3o")),
                ("progresso_percentual", models.PositiveIntegerField(default=0, verbose_name="Progresso na Trilha (%)")),
                (
                    "aluno",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trilhas_matriculadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "trilha",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matriculas",
                        to="ava.trilhaformativa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Matr\u00edcula na Trilha",
                "verbose_name_plural": "Matr\u00edculas nas Trilhas",
                "unique_together": {("trilha", "aluno")},
            },
        ),
        migrations.CreateModel(
            name="AutorizacaoCurso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "papel",
                    models.CharField(
                        choices=[
                            ("gestor", "Gestor/Coordenador"),
                            ("tutor", "Tutor/Autor"),
                            ("avaliador", "Avaliador"),
                        ],
                        default="tutor",
                        max_length=30,
                        verbose_name="Papel de Gest\u00e3o",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "curso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="autorizacoes",
                        to="ava.curso",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="autorizacoes_ava",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Autoriza\u00e7\u00e3o de Curso",
                "verbose_name_plural": "Autoriza\u00e7\u00f5es de Cursos",
                "unique_together": {("curso", "usuario", "papel")},
            },
        ),
        migrations.CreateModel(
            name="AtividadeTentativa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("em_andamento", "Em Andamento"),
                            ("enviada", "Enviada / Aguardando Corre\u00e7\u00e3o"),
                            ("corrigida", "Corrigida"),
                        ],
                        default="em_andamento",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                ("nota_obtida", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Nota Obtida")),
                ("feedback_tutor", models.TextField(blank=True, verbose_name="Feedback do Tutor")),
                ("data_inicio", models.DateTimeField(auto_now_add=True)),
                ("data_envio", models.DateTimeField(blank=True, null=True)),
                ("data_correcao", models.DateTimeField(blank=True, null=True)),
                ("texto_resposta", models.TextField(blank=True, verbose_name="Resposta Discursiva")),
                (
                    "arquivo_enviado",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="ava/tentativas/arquivos/",
                        verbose_name="Arquivo Enviado",
                    ),
                ),
                (
                    "aluno",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="atividades_tentativas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "atividade",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tentativas",
                        to="ava.atividade",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "corrigido_por",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="atividades_corrigidas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Tentativa de Atividade",
                "verbose_name_plural": "Tentativas de Atividades",
                "ordering": ("-data_inicio",),
            },
        ),
        migrations.CreateModel(
            name="QuizRespostaItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("texto_livre", models.TextField(blank=True, verbose_name="Resposta em texto (se aplic\u00e1vel)")),
                ("is_correta", models.BooleanField(default=False, verbose_name="Acertou?")),
                ("nota_item", models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name="Nota neste item")),
                (
                    "alternativa_selecionada",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="selecoes_alunos",
                        to="ava.quizalternativa",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "questao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respostas_alunos",
                        to="ava.quizquestao",
                    ),
                ),
                (
                    "tentativa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respostas_quiz",
                        to="ava.atividadetentativa",
                    ),
                ),
            ],
            options={"unique_together": {("tentativa", "questao")}},
        ),
        migrations.CreateModel(
            name="ProgressoAula",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("is_concluida", models.BooleanField(default=False, verbose_name="Conclu\u00edda?")),
                ("data_inicio", models.DateTimeField(auto_now_add=True)),
                ("data_conclusao", models.DateTimeField(blank=True, null=True)),
                (
                    "aula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progressos_alunos",
                        to="ava.aula",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "matricula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progressos_aulas",
                        to="ava.matriculacurso",
                    ),
                ),
            ],
            options={
                "verbose_name": "Progresso de Aula",
                "verbose_name_plural": "Progressos de Aulas",
                "unique_together": {("matricula", "aula")},
            },
        ),
        migrations.CreateModel(
            name="ProgressoConteudo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("is_visualizado", models.BooleanField(default=False, verbose_name="Visualizado/Conclu\u00eddo?")),
                ("data_visualizacao", models.DateTimeField(blank=True, null=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "conteudo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="visualizacoes",
                        to="ava.conteudoaula",
                    ),
                ),
                (
                    "progresso_aula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conteudos_visualizados",
                        to="ava.progressoaula",
                    ),
                ),
            ],
            options={
                "verbose_name": "Progresso de Conte\u00fado",
                "verbose_name_plural": "Progressos de Conte\u00fados",
                "unique_together": {("progresso_aula", "conteudo")},
            },
        ),
        migrations.CreateModel(
            name="ProgressoModulo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("is_concluido", models.BooleanField(default=False, verbose_name="Conclu\u00eddo?")),
                ("data_inicio", models.DateTimeField(auto_now_add=True)),
                ("data_conclusao", models.DateTimeField(blank=True, null=True)),
                ("percentual", models.PositiveIntegerField(default=0, verbose_name="Progresso do M\u00f3dulo (%)")),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "matricula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progressos_modulos",
                        to="ava.matriculacurso",
                    ),
                ),
                (
                    "modulo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progressos_alunos",
                        to="ava.cursomodulo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Progresso de M\u00f3dulo",
                "verbose_name_plural": "Progressos de M\u00f3dulos",
                "unique_together": {("matricula", "modulo")},
            },
        ),
        migrations.CreateModel(
            name="ConfigCertificado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "template_html",
                    models.TextField(
                        blank=True,
                        help_text="Vari\u00e1veis permitidas: {{aluno}}, {{curso}}, {{carga_horaria}}, {{data}}, etc.",
                        verbose_name="Template HTML",
                    ),
                ),
                (
                    "carga_horaria_impressa",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="0 para usar a carga hor\u00e1ria original do curso/trilha",
                        verbose_name="Carga Hor\u00e1ria Impressa",
                    ),
                ),
                ("assinatura_digital_url", models.URLField(blank=True, verbose_name="URL da Assinatura (Imagem)")),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "curso",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="config_certificado",
                        to="ava.curso",
                    ),
                ),
                (
                    "trilha",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="config_certificado",
                        to="ava.trilhaformativa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configura\u00e7\u00e3o de Certificado",
                "verbose_name_plural": "Configura\u00e7\u00f5es de Certificados",
            },
        ),
        migrations.CreateModel(
            name="Certificado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("codigo_validacao", models.CharField(blank=True, max_length=64, unique=True, verbose_name="C\u00f3digo Valida\u00e7\u00e3o \u00danico")),
                ("data_emissao", models.DateTimeField(auto_now_add=True, verbose_name="Data de Emiss\u00e3o")),
                ("nota_final", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Nota Final no certificado")),
                ("carga_horaria", models.PositiveIntegerField(default=0, verbose_name="Carga Hor\u00e1ria")),
                ("dados_impressos", models.JSONField(blank=True, default=dict, verbose_name="Dados Impressos (Snapshot)")),
                (
                    "arquivo_pdf",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="ava/certificados/pdfs/",
                        verbose_name="Arquivo PDF (Gerado)",
                    ),
                ),
                (
                    "aluno",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificados_ava",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "matricula_curso",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificado_emitido",
                        to="ava.matriculacurso",
                    ),
                ),
                (
                    "matricula_trilha",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificado_emitido",
                        to="ava.matriculatrilha",
                    ),
                ),
            ],
            options={
                "verbose_name": "Certificado",
                "verbose_name_plural": "Certificados",
            },
        ),
        migrations.AddIndex(
            model_name="curso",
            index=models.Index(fields=["cliente", "status", "is_aberto"], name="ava_curso_cli_sta_abr_idx"),
        ),
        migrations.AddIndex(
            model_name="curso",
            index=models.Index(fields=["slug"], name="ava_curso_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="matriculacurso",
            index=models.Index(fields=["cliente", "aluno", "curso"], name="ava_matcurso_cli_alu_cur_idx"),
        ),
        migrations.AddIndex(
            model_name="matriculacurso",
            index=models.Index(fields=["status"], name="ava_matcurso_status_idx"),
        ),
        migrations.AddIndex(
            model_name="matriculatrilha",
            index=models.Index(fields=["cliente", "aluno", "trilha"], name="ava_mattrilha_cli_alu_tri_idx"),
        ),
        migrations.AddIndex(
            model_name="atividadetentativa",
            index=models.Index(fields=["cliente", "aluno", "atividade"], name="ava_ativtent_cli_alu_ati_idx"),
        ),
        migrations.AddIndex(
            model_name="progressoaula",
            index=models.Index(fields=["cliente", "matricula", "aula"], name="ava_progaula_cli_mat_aul_idx"),
        ),
        migrations.AddIndex(
            model_name="certificado",
            index=models.Index(fields=["cliente", "codigo_validacao"], name="ava_cert_cli_cod_idx"),
        ),
        migrations.AddIndex(
            model_name="certificado",
            index=models.Index(fields=["cliente", "aluno"], name="ava_cert_cli_alu_idx"),
        ),
    ]
