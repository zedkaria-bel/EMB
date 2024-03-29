# Generated by Django 3.2 on 2022-04-11 11:39

from django.db import migrations, models
import django_model_changes.changes


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_profile_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Production_Capacite_Imp',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('date', models.DateField(blank=True, null=True)),
                ('arrets', models.IntegerField(blank=True, null=True)),
                ('prod_brute', models.IntegerField(blank=True, null=True)),
                ('shift', models.IntegerField(blank=True, null=True)),
                ('taux_util', models.FloatField(blank=True, null=True)),
                ('capacite_prod', models.IntegerField(blank=True, null=True)),
                ('taux_prod', models.FloatField(blank=True, null=True)),
                ('ligne', models.TextField(blank=True, null=True)),
                ('cph', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'Production_Capacite_Imp',
            },
            bases=(django_model_changes.changes.ChangesMixin, models.Model),
        ),
    ]
