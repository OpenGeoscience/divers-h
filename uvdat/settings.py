from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)


def split_env_str(s: str | None, sep: str) -> list[str]:
    """Split an env string.

    If the string is None or empty, then an empty list is returned.
    """
    return s.split(sep) if s else []


class UvdatMixin(ConfigMixin):
    ASGI_APPLICATION = 'uvdat.asgi.application'
    WSGI_APPLICATION = 'uvdat.wsgi.application'
    ROOT_URLCONF = 'uvdat.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    ACCOUNT_EMAIL_VERIFICATION = 'none'
    ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'

    CHANNEL_LAYERS = {
        'default': {
            # TODO: switch to channels_redis.pubsub.RedisPubSubChannelLayer when it's out of beta
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [
                    {
                        'address': os.environ['REDIS_URL'],
                        'db': 1,
                    }
                ],
            },
        },
    }

    @staticmethod
    def mutate_configuration(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'daphne',
            'django.contrib.gis',
            'django_large_image',
            'uvdat.core.apps.CoreConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            's3_file_field',
        ]

        configuration.REST_FRAMEWORK['DEFAULT_FILTER_BACKENDS'] = [
            'django_filters.rest_framework.DjangoFilterBackend',
        ]
        configuration.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
            'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        ]

        # Re-configure the database for PostGIS
        db_parts = urlparse(os.environ['DJANGO_DATABASE_URL'])
        configuration.DATABASES = {
            'default': {
                'ENGINE': 'django.contrib.gis.db.backends.postgis',
                'NAME': db_parts.path.strip('/'),
                'USER': db_parts.username,
                'PASSWORD': db_parts.password,
                'HOST': db_parts.hostname,
                'PORT': db_parts.port,
            }
        }


class DevelopmentConfiguration(UvdatMixin, DevelopmentBaseConfiguration):
    LOGIN_REDIRECT_URL = os.getenv('LOGIN_REDIRECT_URL', 'http://localhost:3000/')


class TestingConfiguration(UvdatMixin, TestingBaseConfiguration):
    pass


class ProductionConfiguration(UvdatMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(UvdatMixin, HerokuProductionBaseConfiguration):
    pass


class DockerComposeProdConfiguration(UvdatMixin, DevelopmentBaseConfiguration):
    # The prototype docker-compose prod deployment is most similar to the dev configuration
    DEBUG = False

    CSRF_TRUSTED_ORIGINS = split_env_str(os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS'), ',')

    # The following is required to generate correct absolute URLs behind nginx over TLS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
