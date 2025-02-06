# Generated by Django 5.0.7 on 2025-02-04 14:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_netcdfdata_netcdflayer_netcdfimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='VectorFeatureTableData',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('type', models.TextField(blank=True, default='')),
                ('description', models.TextField(blank=True, null=True)),
                ('columns', models.JSONField(blank=True, null=True)),
                ('summary', models.JSONField(blank=True, null=True)),
                (
                    'map_layer',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.vectormaplayer'
                    ),
                ),
                (
                    'vector_feature',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.vectorfeature'
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='VectorFeatureRowData',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('row_data', models.JSONField(blank=True, null=True)),
                (
                    'vector_feature_table',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='core.vectorfeaturetabledata',
                    ),
                ),
            ],
        ),
    ]
