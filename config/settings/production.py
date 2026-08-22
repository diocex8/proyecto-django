"""
settings/production.py

Configuracion exclusiva del entorno de PRODUCCION.
"""

from .base import *  # noqa: F401, F403
import environ
import os
from pathlib import Path

DEBUG = False

env = environ.Env()
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Seguridad HTTP
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'https://*.onrender.com',
    'http://localhost:3000',
    'http://127.0.0.1:8000',
])
if 'https://*.onrender.com' not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append('https://*.onrender.com')

# REST Framework
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',
)

WHITENOISE_MANIFEST_STRICT = False
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# CORS
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = False

# Logging
BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'produccion': {
            'format': '[{asctime}] {levelname} {name} {message}',
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

# Base de datos en produccion via DATABASE_URL
if env('DATABASE_URL', default=None):
    DATABASES['default'] = env.db('DATABASE_URL')
    DATABASES['default']['CONN_MAX_AGE'] = 60
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
        'client_encoding': 'UTF8',
        'options': '-c client_encoding=UTF8',
    }
