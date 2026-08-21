"""Configuracion de la aplicacion de asignaciones."""
from django.apps import AppConfig


class AsignacionesConfig(AppConfig):
    """Configuracion de la aplicacion de asignaciones."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.asignaciones'
    verbose_name = 'Asignaciones'
