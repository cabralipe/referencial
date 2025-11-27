from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0005_tarefa_nome"),
    ]

    operations = [
        migrations.AddField(
            model_name="textocolaborativo",
            name="pergunta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="textos_colaborativos",
                to="curriculum.pergunta",
            ),
        ),
        migrations.AddIndex(
            model_name="textocolaborativo",
            index=models.Index(
                fields=["cliente", "gt", "pergunta"],
                name="curriculum_textocolab_cli_gt_perg_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="textocolaborativo",
            constraint=models.UniqueConstraint(
                condition=models.Q(("pergunta__isnull", False)),
                fields=("cliente", "gt", "pergunta"),
                name="uniq_texto_colaborativo_por_pergunta",
            ),
        ),
    ]
