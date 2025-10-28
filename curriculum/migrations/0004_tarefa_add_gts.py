from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('curriculum', '0003_textocolaborativo'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarefa',
            name='gts',
            field=models.ManyToManyField(blank=True, related_name='tarefas', to='curriculum.gt'),
        ),
    ]
