# Generated by Django 5.0.7 on 2025-03-31 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_netcdfdata_bounds_rastermaplayer_bounds_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DisplayConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled_ui', models.JSONField(default=list, help_text="List of enabled UI elements: 'Collections', 'Datasets', 'Metadata', 'Scenarios'.")),
                ('default_tab', models.CharField(choices=[('Collections', 'Collections'), ('Datasets', 'Datasets'), ('Metadata', 'Metadata'), ('Scenarios', 'Scenarios')], help_text='The default tab must be one of the enabled features.', max_length=256)),
                ('default_displayed_layers', models.JSONField(default=list, help_text="List of map_layers enabled: [{type: 'netcdf', id: 1}. {type: 'vector', id: 3}, {type: 'raster', id: 4}]")),
            ],
        ),
    ]
