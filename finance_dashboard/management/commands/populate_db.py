import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Creates a superuser if it does not exist, using environment variables'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'ngpminhkhang@gmail.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Traucon123@')

        if not User.objects.filter(username=username).exists():
            try:
                call_command(
                    'createsuperuser',
                    '--noinput',
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" already exists'))