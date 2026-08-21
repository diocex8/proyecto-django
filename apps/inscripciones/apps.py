"""Configuracion de la aplicacion de inscripciones."""
from django.apps import AppConfig


class InscripcionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inscripciones'
    verbose_name = 'Inscripciones'
