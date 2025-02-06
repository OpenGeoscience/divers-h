# Generated by Django 5.0.7 on 2025-02-06 16:55

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import s3_file_field.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Context',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255, unique=True)),
                ('default_map_center', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('default_map_zoom', models.IntegerField(default=10)),
                ('indicators', models.JSONField(default=list)),
            ],
        ),
        migrations.CreateModel(
            name='Dataset',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('category', models.CharField(max_length=25)),
                ('processing', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('created', models.TimeField(default=None, null=True)),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LayerCollection',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('configuration', models.JSONField(blank=True, null=True)),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VectorFeature',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('geometry', django.contrib.gis.db.models.fields.GeometryField(srid=4326)),
                ('properties', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Chart',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('chart_data', models.JSONField(blank=True, null=True)),
                ('chart_options', models.JSONField(blank=True, null=True)),
                ('editable', models.BooleanField(default=False)),
                (
                    'context',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='charts',
                        to='core.context',
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='context',
            name='datasets',
            field=models.ManyToManyField(blank=True, to='core.dataset'),
        ),
        migrations.CreateModel(
            name='FileItem',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('file', s3_file_field.fields.S3FileField()),
                ('file_type', models.CharField(max_length=25)),
                ('file_size', models.PositiveBigIntegerField(null=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('index', models.IntegerField(null=True)),
                (
                    'chart',
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='core.chart'
                    ),
                ),
                (
                    'dataset',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='source_files',
                        to='core.dataset',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='NetCDFData',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('default_style', models.JSONField(blank=True, null=True)),
                ('index', models.IntegerField(null=True)),
                ('name', models.CharField(blank=True, max_length=255)),
                (
                    'dataset',
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='core.dataset'
                    ),
                ),
                (
                    'file_item',
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='core.fileitem'
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='NetCDFLayer',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(blank=True, max_length=255)),
                ('parameters', models.JSONField()),
                ('description', models.TextField(blank=True, null=True)),
                ('color_scheme', models.CharField(blank=True, max_length=255)),
                (
                    'bounds',
                    django.contrib.gis.db.models.fields.PolygonField(
                        blank=True, help_text='Bounds/Extents of NetCDFLayer', null=True, srid=4326
                    ),
                ),
                (
                    'netcdf_data',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.netcdfdata'
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='NetCDFImage',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('image', s3_file_field.fields.S3FileField()),
                ('slider_index', models.IntegerField()),
                (
                    'bounds',
                    django.contrib.gis.db.models.fields.PolygonField(
                        blank=True, help_text='Bounds/Extents of NetCDFLayer', null=True, srid=4326
                    ),
                ),
                (
                    'netcdf_layer',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='core.netcdflayer',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Network',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('category', models.CharField(max_length=25)),
                ('metadata', models.JSONField(blank=True, null=True)),
                (
                    'dataset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='networks',
                        to='core.dataset',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='NetworkNode',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('capacity', models.IntegerField(null=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                (
                    'network',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='nodes',
                        to='core.network',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='NetworkEdge',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('capacity', models.IntegerField(null=True)),
                ('line_geometry', django.contrib.gis.db.models.fields.LineStringField(srid=4326)),
                ('directed', models.BooleanField(default=False)),
                (
                    'network',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='edges',
                        to='core.network',
                    ),
                ),
                (
                    'from_node',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='+',
                        to='core.networknode',
                    ),
                ),
                (
                    'to_node',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='+',
                        to='core.networknode',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='ProcessingTask',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, null=True)),
                (
                    'status',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('Complete', 'Complete'),
                            ('Running', 'Running'),
                            ('Error', 'Error'),
                            ('Queued', 'Queued'),
                        ],
                        help_text='Processing Status',
                        max_length=255,
                    ),
                ),
                (
                    'celery_id',
                    models.CharField(blank=True, help_text='Celery Task Id', max_length=255),
                ),
                ('output_metadata', models.JSONField(blank=True, null=True)),
                ('error', models.TextField(blank=True, help_text='Error text if an error occurs')),
                ('file_items', models.ManyToManyField(blank=True, to='core.fileitem')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RasterMapLayer',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('default_style', models.JSONField(blank=True, null=True)),
                ('index', models.IntegerField(null=True)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('cloud_optimized_geotiff', s3_file_field.fields.S3FileField()),
                (
                    'dataset',
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='core.dataset'
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SimulationResult',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'simulation_type',
                    models.CharField(
                        choices=[
                            ('FLOOD_1', 'Flood Scenario 1'),
                            ('RECOVERY', 'Recovery Scenario'),
                        ],
                        max_length=8,
                    ),
                ),
                ('input_args', models.JSONField(blank=True, null=True)),
                ('output_data', models.JSONField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                (
                    'context',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='simulation_results',
                        to='core.context',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SourceRegion',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('boundary', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                (
                    'dataset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='regions',
                        to='core.dataset',
                    ),
                ),
            ],
        ),
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
        migrations.CreateModel(
            name='VectorMapLayer',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('default_style', models.JSONField(blank=True, null=True)),
                ('index', models.IntegerField(null=True)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('geojson_file', s3_file_field.fields.S3FileField(null=True)),
                (
                    'dataset',
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='core.dataset'
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='vectorfeaturetabledata',
            name='map_layer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='core.vectormaplayer'
            ),
        ),
        migrations.AddField(
            model_name='vectorfeature',
            name='map_layer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='core.vectormaplayer'
            ),
        ),
        migrations.CreateModel(
            name='DerivedRegion',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('boundary', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                (
                    'operation',
                    models.CharField(
                        choices=[('UNION', 'Union'), ('INTERSECTION', 'Intersection')],
                        max_length=12,
                    ),
                ),
                (
                    'context',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='derived_regions',
                        to='core.context',
                    ),
                ),
                (
                    'source_regions',
                    models.ManyToManyField(related_name='derived_regions', to='core.sourceregion'),
                ),
                (
                    'map_layer',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to='core.vectormaplayer'
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='LayerRepresentation',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('object_id', models.PositiveIntegerField()),
                ('default_style', models.JSONField(blank=True, null=True)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('enabled', models.BooleanField(default=True)),
                (
                    'map_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'
                    ),
                ),
            ],
            options={
                'indexes': [
                    models.Index(
                        fields=['map_type', 'object_id'], name='core_layerr_map_typ_b22956_idx'
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='sourceregion',
            constraint=models.UniqueConstraint(
                fields=('dataset', 'name'), name='unique-source-region-name'
            ),
        ),
        migrations.AddConstraint(
            model_name='derivedregion',
            constraint=models.UniqueConstraint(
                fields=('context', 'name'), name='unique-derived-region-name'
            ),
        ),
    ]
