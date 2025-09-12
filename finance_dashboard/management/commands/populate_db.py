import os
     from django.contrib.auth.models import User
     from django.core.management.base import BaseCommand
     from django.core.management import call_command

     class Command(BaseCommand):
         def handle(self, *args, **options):
             if not User.objects.filter(username=os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')).exists():
                 call_command('createsuperuser', '--noinput', '--username', os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin'), '--email', os.environ.get('DJANGO_SUPERUSER_EMAIL', 'abcadmin@gmail.com'))
             self.stdout.write(self.style.SUCCESS('Superuser created successfully'))