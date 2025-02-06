# flake8: noqa: E501
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict
import zipfile

from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
import requests

from uvdat.core.models import Context, Dataset, FileItem

DATA_FOLDER = Path(os.environ.get('NZ_INGEST_BIND_MOUNT_POINT', 'sample_data'))


class Command(BaseCommand):
    help = 'Ingest contexts, datasets, and attach files based on a context.json file'

    def add_arguments(self, parser) -> None:
        parser.add_argument('file_path', type=str, help='Path to the context.json file')
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing data instead of skipping or updating.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Replace ALL data in the current database.',
        )

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        file_path = Path(DATA_FOLDER, options['file_path'])
        if not file_path.exists():
            self.stderr.write(f'File {file_path} does not exist.')
            return

        replace = options.get('replace', False)
        replace_all = options.get('clear', False)
        if replace_all:
            confirm = input(
                "Are you sure you want to delete ALL Context and Dataset models? Type 'yes' to confirm: "
            )
            if confirm.lower() == 'yes':
                Context.objects.all().delete()
                Dataset.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS('Successfully deleted all Context and Dataset models')
                )
            else:
                self.stdout.write(self.style.WARNING('Aborted deletion of models'))
                return
        with file_path.open('r') as f:
            data = json.load(f)

        for entry in data:
            if entry['type'] == 'Context':
                self.create_or_update_context(entry, replace)
            elif entry['type'] == 'Dataset':
                self.create_or_update_dataset(entry, None, replace)
            else:
                self.stderr.write(
                    self.style.WARNING(f'Unknown type {entry["type"]} in the dataset.')
                )

    def create_or_update_context(self, context_data: Dict[str, Any], replace: bool) -> None:
        context_name = context_data['name']
        action = context_data.get('action')
        if action in ['delete', 'replace']:
            exists = Context.objects.get(name=context_name)
            if exists:
                exists.delete()
            else:
                self.style.WARNING(
                    f'\t WARNING!!! Attempting to delete Context: {context_name} and it does not exist'
                )
            if action == 'delete':
                return
        context, created = Context.objects.get_or_create(
            name=context_name,
            defaults={
                'default_map_center': Point(*context_data['default_map_center']),
                'default_map_zoom': context_data['default_map_zoom'],
                'indicators': context_data.get('indicators', []),
            },
        )

        if created:
            self.stdout.write(f'Created context {context_name}')
        elif replace:
            self.stdout.write(f'Context {context_name} already exists and will be replaced.')
            context.default_map_center = Point(*context_data['default_map_center'])
            context.default_map_zoom = context_data['default_map_zoom']
            context.indicators = context_data.get('indicators', [])
            context.save()
        else:
            self.stdout.write(f'Context {context_name} already exists and will not be replaced.')
        for dataset_data in context_data.get('datasets', []):
            self.create_or_update_dataset(dataset_data, context, replace)

    def create_or_update_dataset(
        self, dataset_data: Dict[str, Any], context: Context | None, replace: bool
    ) -> None:
        dataset_name = dataset_data['name']
        action = dataset_data.get('action')
        if action in ['delete', 'replace']:
            exists = Dataset.objects.get(name=dataset_name)
            if exists:
                exists.delete()
            else:
                self.style.WARNING(
                    f'\t WARNING!!! Attempting to delete Dataset: {dataset_name} and it does not exist'
                )
            if action == 'delete':
                self.stdout.write(f'Dataset {dataset_name} is being deleted')
                return
        dataset, created = Dataset.objects.get_or_create(
            name=dataset_name,
            defaults={
                'description': dataset_data['description'],
                'category': dataset_data['category'],
                'metadata': dataset_data.get('metadata', {}),
            },
        )

        if created:
            self.stdout.write(f'Created dataset {dataset_name}')
        elif replace:
            self.stdout.write(f'Dataset {dataset_name} already exists and will be replaced.')
            dataset.delete()
            dataset, created = Dataset.objects.get_or_create(
                name=dataset_name,
                defaults={
                    'description': dataset_data['description'],
                    'category': dataset_data['category'],
                    'metadata': dataset_data.get('metadata', {}),
                },
            )
        else:
            self.stdout.write(f'Dataset {dataset_name} already exists and will not be replaced.')
        default_style = dataset_data.get('default_style', None)
        # Attach dataset to context
        if context and not context.datasets.filter(id=dataset.id).exists():
            context.datasets.add(dataset)
            self.stdout.write(f'Attached dataset {dataset_name} to context {context.name}')

        results = []
        for index, file_info in enumerate(dataset_data.get('files', [])):
            result = self.ingest_file(file_info, dataset, index, replace)
            if result:
                results.append(result)
            else:
                return False
        if all(results):
            self.stdout.write(f'Spawning Conversion Task for {dataset_name}')
            dataset.spawn_conversion_task(
                asynchronous=False,
                style_options=default_style,
            )
        else:
            self.stdout.write(f'Skipping Conversion Task for {dataset_name}')

    def ingest_file(
        self, file_info: Dict[str, Any], dataset: Dataset, index: int, replace: bool
    ) -> None:
        file_path = file_info.get('path')
        file_url = file_info.get('url')
        file_metadata = file_info.get('metadata', {})
        action = file_info.get('action')
        is_file_list = isinstance(file_path, list)
        if (
            not file_url and file_info.get('type') == 'shp' and not is_file_list
        ):  # try to find relative files
            extension_list = ['.dbf', '.prj', '.shx']
            base_file = file_path
            if not base_file.endswith('.shp'):
                self.stderr.write(
                    '\t Using type shp, the base file should be a .shp file;'
                    f' is instead: {base_file}'
                )
                return False

            file_path = [base_file]
            for extension in extension_list:
                extension_file = base_file.replace('.shp', extension)
                extension_path = Path(DATA_FOLDER, extension_file)
                if not os.path.exists(extension_path):
                    self.stderr.write(
                        '\t Shape file indicated without URL and single file, '
                        f'cannot find file: {extension_file}'
                    )
                    return
                else:
                    file_path.append(extension_file)
            is_file_list = True

        if is_file_list and file_info.get('name', False) is False:
            self.stderr.write('\tWhen using an array for file_path, a "name" key must be included')
        if not is_file_list:
            file_name = file_info.get('name', file_path.split('/')[-1])
        else:
            file_name = file_info['name']

        if isinstance(file_path, list):  # download and zip files together if required
            if file_url and not isinstance(file_url, list):
                self.stderr.write(
                    f'\tFileItem {file_path} is an Array and URL exists but is not an Array'
                )
                return False
            elif file_url and len(file_path) != len(file_url):
                self.stderr.write(
                    f'\tFileItem length: {len(file_path)} and '
                    f'file_url length: {len(file_url)} are not the same'
                )
                return False
            for sub_index, item in enumerate(file_path):
                subfile_location = Path(DATA_FOLDER, item)
                # download files if they don't exists in the location
                if not subfile_location.exists():
                    self.stdout.write(
                        f'\tDownloading data file {item} from url: {file_url[sub_index]}.'
                    )
                    subfile_location.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with open(subfile_location, 'wb') as f:
                            r = requests.get(file_url[sub_index])
                            r.raise_for_status()
                            f.write(r.content)
                    except requests.exceptions.RequestException as error:
                        self.stdout.write(
                            self.style.WARNING(
                                f'\t WARNING!!! There was an error downloading url: {file_url[sub_index]} - {error}'
                            )
                        )
                        dataset.delete()
                        return False

            # now we zip up the downloaded files
            relative_zip_location = file_path[0].replace(
                os.path.basename(file_path[0]), f'{file_name}.zip'
            )
            zip_filename = Path(DATA_FOLDER, relative_zip_location)
            if os.path.exists(zip_filename):  # Clear if exisitng zip file
                os.remove(zip_filename)
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                # Iterate over the list of files
                for file in file_path:
                    subfile_location = Path(DATA_FOLDER, file)
                    # Add each file to the zip archive
                    if os.path.exists(subfile_location):
                        zipf.write(subfile_location, os.path.basename(subfile_location))
                    else:
                        print(f'File {file} does not exist.')
                zipf.close()

            file_location = zip_filename
            file_type = 'zip'
            file_path = relative_zip_location
        else:
            file_location = Path(DATA_FOLDER, file_path)
            file_type = file_path.split('.')[-1]

            if file_url and not file_location.exists():
                self.stdout.write(f'\tDownloading data file {file_name} using url: {file_url}. ')
                file_location.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(file_location, 'wb') as f:
                        r = requests.get(file_url)
                        r.raise_for_status()
                        f.write(r.content)
                except requests.exceptions.RequestException as error:
                    self.stdout.write(
                        self.style.WARNING(
                            f'\t WARNING!!! There was an error downloading url: {file_url} - {error}'
                        )
                    )
                    dataset.delete()
                    return False
            elif not file_location.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'\t WARNING!!! File does not exist {file_name} at location: {file_location} and no URL is included, removing dataset and skipping'
                    )
                )
                dataset.delete()
                return False

        existing = FileItem.objects.filter(name=file_name, dataset=dataset)
        if existing.exists():
            if replace or action in ['delete', 'replace']:
                self.stdout.write(f'\tFileItem {file_name} exists and will be deleted/replaced.')
                existing.delete()
                if action == 'delete':
                    return
            else:
                self.stdout.write(
                    f'\tFileItem {file_name} already exists and will not be replaced.'
                )
                return False

        new_file_item = FileItem.objects.create(
            name=file_name,
            dataset=dataset,
            index=index,
            file_type=file_type,
            file_size=os.path.getsize(file_location),
            metadata=dict(
                **file_metadata,
                uploaded=str(datetime.now()),
            ),
        )
        self.stdout.write(f'\tFileItem {new_file_item.name} created.')
        with file_location.open('rb') as f:
            new_file_item.file.save(file_path, ContentFile(f.read()))

        # process tabular and add file if needed
        if file_metadata.get('tabular'):
            self.process_tabular_data(new_file_item, dataset, file_metadata, replace, action)
        return True

    def process_tabular_data(self, new_file_item, dataset, file_metadata, replace, action):
        tabular_metadata = file_metadata.get('tabular')
        tabular_url = tabular_metadata.get('url')
        tabular_path = tabular_metadata.get('path')
        tabular_name = tabular_metadata.get('name')
        # download or process the local file
        file_location = Path(DATA_FOLDER, tabular_path)

        if tabular_url and not file_location.exists():
            self.stdout.write(f'\tDownloading data file {tabular_name} using url: {tabular_url}. ')
            file_location.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(file_location, 'wb') as f:
                    r = requests.get(tabular_url)
                    r.raise_for_status()
                    f.write(r.content)
            except requests.exceptions.RequestException as error:
                self.stdout.write(
                    self.style.WARNING(
                        f'\t WARNING!!! There was an error downloading url: {tabular_url} - {error}'
                    )
                )
                dataset.delete()
                return False
        elif not file_location.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'\t WARNING!!! File does not exist {tabular_name} at location: {file_location} and no URL is included, removing dataset and skipping'
                )
            )
            return False

        existing = FileItem.objects.filter(name=tabular_name, dataset=dataset)
        if existing.exists():
            if replace or action in ['delete', 'replace']:
                self.stdout.write(f'\tFileItem {tabular_name} exists and will be deleted/replaced.')
                existing.delete()
                if action == 'delete':
                    return
            else:
                self.stdout.write(
                    f'\tFileItem {tabular_name} already exists and will not be replaced.'
                )
                return False

        tabular_file_item = FileItem.objects.create(
            name=tabular_name,
            dataset=dataset,
            index=0,
            file_type='tabular',
            file_size=os.path.getsize(file_location),
            metadata=dict(
                **tabular_metadata,
                uploaded=str(datetime.now()),
            ),
        )
        self.stdout.write(f'\tFileItem {tabular_file_item.name} created.')
        with file_location.open('rb') as f:
            tabular_file_item.file.save(tabular_path, ContentFile(f.read()))

        # Now lets update the base fileMetadat with the tabular fileitemId
        if 'tabular' in new_file_item.metadata:
            new_file_item.metadata['tabular']['fileItemId'] = tabular_file_item.pk
            new_file_item.save()
