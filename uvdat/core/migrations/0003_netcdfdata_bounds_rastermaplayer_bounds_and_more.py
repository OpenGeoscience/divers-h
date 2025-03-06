# Generated by Django 5.0.7 on 2025-03-06 20:07

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_netcdflayer_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='netcdfdata',
            name='bounds',
            field=django.contrib.gis.db.models.fields.PolygonField(blank=True, help_text='Bounds/Extents of the Layer', null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='rastermaplayer',
            name='bounds',
            field=django.contrib.gis.db.models.fields.PolygonField(blank=True, help_text='Bounds/Extents of the Layer', null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='vectormaplayer',
            name='bounds',
            field=django.contrib.gis.db.models.fields.PolygonField(blank=True, help_text='Bounds/Extents of the Layer', null=True, srid=4326),
        ),
    ]
