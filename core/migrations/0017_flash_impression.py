# Generated by Django 3.2 on 2022-04-14 12:40

from django.db import migrations, models
import django_model_changes.changes


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20220412_1338'),
    ]

    operations = [
        migrations.CreateModel(
            name='Flash_Impression',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('shift', models.TextField(blank=True, null=True)),
                ('format_fer', models.TextField(blank=True, null=True)),
                ('des', models.TextField(blank=True, null=True)),
                ('nb_psg', models.IntegerField(blank=True, null=True)),
                ('sf_brut', models.IntegerField(blank=True, null=True)),
                ('sf_rebut', models.IntegerField(blank=True, null=True)),
                ('sf_conf', models.IntegerField(blank=True, null=True)),
                ('sf_taux_reb', models.IntegerField(blank=True, null=True)),
                ('brut', models.IntegerField(blank=True, null=True)),
                ('rebut', models.IntegerField(blank=True, null=True)),
                ('conf', models.IntegerField(blank=True, null=True)),
                ('taux_reb', models.IntegerField(blank=True, null=True)),
                ('conduct', models.TextField(blank=True, null=True)),
                ('ligne', models.TextField(blank=True, null=True)),
                ('date', models.DateField(blank=True, null=True)),
            ],
            bases=(django_model_changes.changes.ChangesMixin, models.Model),
        ),
    ]
