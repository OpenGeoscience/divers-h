from django.db import models


class DisplayConfiguration(models.Model):
    ENABLED_FEATURES_CHOICES = [
        ('Collections', 'Collections'),
        ('Datasets', 'Datasets'),
        ('Metadata', 'Metadata'),
    ]

    enabled_ui = models.JSONField(
        default=list,
        help_text="List of enabled UI elements: 'Collections', 'Datasets', 'Metadata'.",
    )

    default_tab = models.CharField(
        max_length=256,
        choices=ENABLED_FEATURES_CHOICES,
        help_text='The default tab must be one of the enabled features.',
    )

    default_displayed_layers = models.JSONField(
        default=list,
        help_text="List of map_layers enabled: [{type: 'netcdf', id: 1}. {type: 'vector', id: 3}, {type: 'raster', id: 4}]",
    )

    def clean(self):
        """Ensure default_tab is within enabled_features."""
        super().clean()
        if self.default_tab not in self.enabled_features:
            raise ValueError('The default tab must be one of the enabled features.')

    def __str__(self):
        return f"Configuration ({', '.join(self.enabled_features)})"
