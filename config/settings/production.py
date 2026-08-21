"""
settings/production.py

Configuracion exclusiva del entorno de PRODUCCION.
Aplica las configuraciones de seguridad criticas que no deben estar activas
en desarrollo para no interferir con el flujo de trabajo local.

Principio de seguridad: en caso de duda, denegar. Cada configuracion
aqui presente reduce la superficie de ataque del servidor.
"""

from .base import *  # noqa: F401, F403

import environ
import os
from pathlib import Path

# ===========================================================================
# Configuraciones basicas de produccion
# ===========================================================================

DEBUG = False

# Carga ALLOWED_HOSTS desde variable de entorno (lista separada por comas)
env = environ.Env()
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# ===========================================================================
# Seguridad HTTP (cabeceras de seguridad)
# ===========================================================================

# Redirige todo trafico HTTP a HTTPS
SECURE_SSL_REDIRECT = True

# Indica al navegador que solo se comunique por HTTPS durante 1 ano
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Proteccion contra clickjacking
X_FRAME_OPTIONS = 'DENY'

# Evita que el navegador infiera el tipo MIME
SECURE_CONTENT_TYPE_NOSNIFF = True

# Cookie de sesion solo viaja por HTTPS
SESSION_COOKIE_SECURE = True

# Cookie de CSRF solo viaja por HTTPS
CSRF_COOKIE_SECURE = True

# Origenes de confianza para peticiones CSRF (incluir protocolo + dominio)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ===========================================================================
# CORS en produccion
# ===========================================================================

# Solo los origenes listados en .env pueden consumir la API
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# No permitir cookies en solicitudes CORS cruzadas (API stateless con JWT)
CORS_ALLOW_CREDENTIALS = False

# ===========================================================================
# Logging en produccion: solo WARNING y superiores, a archivos
# ===========================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'produccion': {
            'format': '[{asctime}] {levelname} {name} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'consola': {
            'class': 'logging.StreamHandler',
            'formatter': 'produccion',
        },
    },
    'root': {
        'handlers': ['consola'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['consola'],
            'level': 'WARNING',
            'propagate': False,
        },
        'gestion_academica': {
            'handlers': ['consola'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ===========================================================================
# Base de datos
# ===========================================================================
# Usa la variable de entorno DATABASE_URL. Si existe, sobrescribe la configuracion base.
if env('DATABASE_URL', default=None):
    DATABASES['default'] = env.db('DATABASE_URL')
    DATABASES['default']['CONN_MAX_AGE'] = 60
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
        'client_encoding': 'UTF8',
        'options': '-c client_encoding=UTF8',
    }
