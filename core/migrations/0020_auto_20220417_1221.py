# Generated by Django 3.2 on 2022-04-17 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_flash_impression'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flash_impression',
            name='sf_taux_reb',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='flash_impression',
            name='taux_reb',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
