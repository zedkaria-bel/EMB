# Generated by Django 3.2 on 2022-03-06 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_auto_20220228_1436'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObjectifCapaciteProduction',
            fields=[
                ('id', models.IntegerField(db_column='ID', primary_key=True, serialize=False)),
                ('unite', models.TextField(blank=True, db_column='Unité', null=True)),
                ('obj', models.BigIntegerField(blank=True, db_column='Objectif', null=True)),
                ('capacite_jour', models.BigIntegerField(blank=True, db_column='Capacité jour', null=True)),
                ('date', models.DateField(blank=True, null=True)),
                ('volume', models.TextField(blank=True, db_column='Volume', null=True)),
                ('category', models.TextField(blank=True, null=True)),
                ('produit', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'OBJ_CAP_PRODUCTION',
                'abstract': False,
            },
        ),
    ]
