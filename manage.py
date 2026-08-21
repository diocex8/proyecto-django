#!/usr/bin/env python
"""Utilidad de linea de comandos de Django para tareas administrativas."""
import os
import sys


def main():
    """Ejecuta tareas administrativas."""
    # Selecciona el modulo de settings segun la variable DJANGO_ENVIRONMENT.
    # Si no esta definida, usa development como valor seguro por defecto.
    entorno = os.environ.get('DJANGO_ENVIRONMENT', 'development')
    modulo_settings = f'config.settings.{entorno}'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', modulo_settings)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Asegurate de que este instalado y "
            "disponible en tu PYTHONPATH. Recuerda activar el entorno virtual."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
