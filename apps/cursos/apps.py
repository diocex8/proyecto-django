"""Configuracion de la aplicacion de cursos."""
from django.apps import AppConfig


class CursosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cursos'
    verbose_name = 'Cursos'
