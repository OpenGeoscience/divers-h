# Generated by Django 5.0.7 on 2024-10-17 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_layercollection_layerrepresentation'),
    ]

    operations = [
        migrations.AddField(
            model_name='context',
            name='indicators',
            field=models.JSONField(default=list),
        ),
    ]
