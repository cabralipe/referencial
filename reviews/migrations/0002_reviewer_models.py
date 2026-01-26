from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewerAssignment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("trail", "Trilha"),
                            ("etapa", "Etapa"),
                            ("componente", "Componente"),
                            ("ppp", "PPP"),
                        ],
                        max_length=20,
                    ),
                ),
                ("scope_id", models.CharField(max_length=64)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviewerassignments",
                        to="core.cliente",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviewer_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="ReviewDecision",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("resposta", "Resposta"),
                            ("texto_unico", "Texto Unico"),
                            ("quadro", "Quadro"),
                        ],
                        max_length=20,
                    ),
                ),
                ("target_id", models.CharField(max_length=36)),
                (
                    "actor_role",
                    models.CharField(
                        choices=[
                            ("reviewer", "Revisor"),
                            ("redactor", "Redator"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "decision_type",
                    models.CharField(
                        choices=[
                            ("recommend_approve", "Recomendar validacao"),
                            ("recommend_return", "Recomendar devolucao"),
                            ("recommend_minor", "Recomendar ajustes menores"),
                            ("in_progress", "Em andamento"),
                        ],
                        max_length=30,
                    ),
                ),
                ("checklist", models.JSONField(blank=True, default=list)),
                ("note", models.TextField(blank=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="review_decisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviewdecisions",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="reviewerassignment",
            index=models.Index(fields=["cliente", "reviewer", "scope_type", "scope_id"], name="reviews_rev_cliente_5c3d66_idx"),
        ),
        migrations.AddIndex(
            model_name="reviewdecision",
            index=models.Index(fields=["cliente", "target_type", "target_id"], name="reviews_rev_cliente_2f9a8f_idx"),
        ),
        migrations.AddIndex(
            model_name="reviewdecision",
            index=models.Index(fields=["cliente", "actor_role", "created_at"], name="reviews_rev_cliente_3f8df6_idx"),
        ),
    ]
