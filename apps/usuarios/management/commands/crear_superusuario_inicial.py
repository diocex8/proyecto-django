import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Crea un superusuario inicial si no existe ninguno en la base de datos'

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.environ.get('ADMIN_EMAIL', 'admin@admin.com')
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', 'Admin123456!')

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
                first_name='Admin',
                last_name='Sistema',
                rol=User.Rol.ADMINISTRADOR
            )
            self.stdout.write(self.style.SUCCESS(f'Superusuario {email} creado exitosamente.'))
        else:
            self.stdout.write(self.style.NOTICE('Ya existe al menos un superusuario. Omitiendo.'))
