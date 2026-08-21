"""
settings/development.py

Configuracion exclusiva del entorno de DESARROLLO LOCAL.
Hereda todo de base.py y sobreescribe solo lo necesario para facilitar
la depuracion sin comprometer la seguridad del entorno de produccion.
"""

from .base import *  # noqa: F401, F403

# ===========================================================================
# Modo debug activado solo en desarrollo
# ===========================================================================

DEBUG = True

# En desarrollo se acepta cualquier host (solo local)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# ===========================================================================
# Herramientas de desarrollo adicionales
# ===========================================================================

# Se agrega django-debug-toolbar si esta instalado
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass

# ===========================================================================
# Renderer navegable en desarrollo (permite usar el DRF Browsable API)
# ===========================================================================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

# Agrega SessionAuthentication en desarrollo para que el boton "Log in"
# aparezca en la API navegable del navegador. En produccion solo JWT es valido.
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',
)

# ===========================================================================
# Email: consola en desarrollo (no envia correos reales)
# ===========================================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ===========================================================================
# Logging en desarrollo: nivel DEBUG, salida en consola
# ===========================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detallado': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'consola': {
            'class': 'logging.StreamHandler',
            'formatter': 'detallado',
        },
    },
    'root': {
        'handlers': ['consola'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['consola'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            # Nivel DEBUG aqui muestra TODAS las consultas SQL en la consola.
            # Muy util para detectar problemas N+1 durante el desarrollo.
            'level': 'DEBUG',
            'handlers': ['consola'],
            'propagate': False,
        },
        # Logger propio del proyecto
        'gestion_academica': {
            'handlers': ['consola'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
