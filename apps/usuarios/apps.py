"""Configuracion de la aplicacion de usuarios."""
from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Ruta completa del modulo porque la app vive dentro de apps/
    name = 'apps.usuarios'
    verbose_name = 'Usuarios'
