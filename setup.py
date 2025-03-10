from pathlib import Path

from setuptools import find_packages, setup

readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with readme_file.open() as f:
        long_description = f.read()
else:
    # When this is first installed in development Docker, README.md is not available
    long_description = ''

setup(
    name='uvdat',
    version='0.1.0',
    description='',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.0',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python',
    ],
    python_requires='>=3.10',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Pinned August 2024
        'celery==5.4.0',
        'django==5.0.7',
        'django-configurations[database,email]==2.5.1',
        'django-extensions==3.2.3',
        'django-filter==24.3',
        'django-oauth-toolkit==2.4.0',
        'djangorestframework==3.15.2',
        'django-large-image==0.10.0',
        'drf-yasg==1.21.7',
        'fiona==1.10.0',
        'osmnx==1.9.4',
        'geopandas==0.14.4',
        'networkx==3.3',
        'pyshp==2.3.1',
        'rasterio==1.3.10',
        'urllib3==1.26.15',
        'webcolors==24.6.0',
        # netCDF tools
        'xarray==2024.11.0',
        'netCDF4==1.7.2',
        'h5netcdf==1.4.1',
        'matplotlib==3.9.3',
        'scipy==1.15.1',
        'cftime==1.6.4',
        'pydap==3.5.3',
        'iris==1.0.7',
        # Production-only
        'django-composed-configuration[prod]==0.25.0',
        'django-s3-file-field[boto3]==1.0.1',
        'gunicorn==22.0.0',
    ],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]==0.25.0',
            'django-debug-toolbar==4.4.6',
            'django-s3-file-field[minio]==1.0.1',
            'ipython==8.26.0',
            'tox==4.16.0',
        ],
    },
)
