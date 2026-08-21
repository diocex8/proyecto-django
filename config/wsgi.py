"""
Punto de entrada WSGI para el proyecto.
Gunicorn usa este archivo en produccion para servir la aplicacion.
La variable DJANGO_ENVIRONMENT determina el modulo de settings activo.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

entorno = os.environ.get('DJANGO_ENVIRONMENT', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'config.settings.{entorno}')

application = get_wsgi_application()
