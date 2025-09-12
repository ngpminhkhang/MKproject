import os
     from django.contrib.auth.models import User
     from django.core.management.base import BaseCommand
     from django.core.management import call_command

     class Command(BaseCommand):
         def handle(self, *args, **options):
             username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
             email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'abcadmin@gmail.com')
             password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Traucon123@')
             if not User.objects.filter(username=username).exists():
                 call_command('createsuperuser', '--noinput', username=username, email=email, password=password)
             self.stdout.write(self.style.SUCCESS('Superuser created successfully'))