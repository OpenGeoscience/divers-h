from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from oauth2_provider.models import Application

CLIENT_ID = 'devClientId'  # overrride using arguments when in prod


class Command(BaseCommand):
    help = 'Create a Django OAuth Toolkit application (client)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            required=True,
            help='Superuser username for application creator',
        )
        parser.add_argument(
            '--uri',
            type=str,
            default='http://localhost:3000/',
            help='Redirect URI for application',
        )
        parser.add_argument(
            '--name',
            type=str,
            default='divers-h-client',
            help='Name of the application',
        )

        parser.add_argument(
            '--id',
            type=str,
            default=CLIENT_ID,
            help='Redirect URI for application',
        )

    def handle(self, *args, **options):
        username = options['username']
        uri = options['uri']
        id = options['id']
        name = options['name']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % username)

        application, created = Application.objects.update_or_create(
            client_id=id,
            defaults={
                'name': name,
                'client_secret': '',
                'client_type': 'public',
                'redirect_uris': uri,
                'authorization_grant_type': 'authorization-code',
                'user': user,
                'skip_authorization': True,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created application "{application.name}"')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated application "{application.name}"')
            )
