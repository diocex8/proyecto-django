"""
settings/base.py

Configuracion base compartida entre TODOS los entornos (desarrollo, produccion).
Contiene los valores comunes y no sensibles. Los valores sensibles se cargan
desde el archivo .env mediante django-environ.

Decision de arquitectura:
    - Se usa django-environ para separar la configuracion del codigo fuente.
    - Esto cumple con el principio de 12-Factor App (factor III: Config).
    - Las credenciales NUNCA se escriben directamente en el codigo.
"""

import os
from pathlib import Path

import environ

# ===========================================================================
# Rutas base del proyecto
# ===========================================================================

# BASE_DIR apunta a la raiz del proyecto (donde esta manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ===========================================================================
# Carga de variables de entorno con django-environ
# ===========================================================================

env = environ.Env(
    # Valores predeterminados seguros para variables booleanas y de tipo
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Carga el archivo .env desde la raiz del proyecto
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ===========================================================================
# Clave secreta de Django
# ===========================================================================

# Leida desde .env. Si no existe, lanzara un ImproperlyConfigured en produccion.
SECRET_KEY = env('SECRET_KEY')

# ===========================================================================
# Aplicaciones instaladas
# ===========================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
]

# Aplicaciones propias del proyecto. Se usan rutas de modulo completas
# porque las apps estan dentro del directorio 'apps/'.
LOCAL_APPS = [
    'apps.usuarios',
    'apps.cursos',
    'apps.inscripciones',
    'apps.asignaciones',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ===========================================================================
# Middlewares
# ===========================================================================

MIDDLEWARE = [
    # CorsMiddleware debe ir ANTES de CommonMiddleware
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise se inserta aqui para servir estaticos en produccion
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

# ===========================================================================
# Templates (necesario para el panel de administracion de Django)
# ===========================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ===========================================================================
# Base de datos PostgreSQL
# ===========================================================================

# Decision: Se usa PostgreSQL en todos los entornos (incluyendo desarrollo)
# para garantizar paridad entre entornos y evitar errores de comportamiento
# que difieren entre SQLite y PostgreSQL (ej. tipos de campo, constraints).

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default=''),
        'USER': env('DB_USER', default=''),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
        'OPTIONS': {
            # Evita que las conexiones queden en estado idle indefinidamente
            'connect_timeout': 10,
            # Fuerza codificacion UTF-8 en la conexion.
            # Necesario en Windows con psycopg2 cuando la contrasena
            # contiene caracteres especiales o el locale del sistema
            # no es UTF-8.
            'client_encoding': 'UTF8',
            'options': '-c client_encoding=UTF8',
        },
        'CONN_MAX_AGE': 60,  # Reutilizar conexiones por 60 segundos
    }
}

# ===========================================================================
# Modelo de usuario personalizado
# ===========================================================================

# Decision critica: AUTH_USER_MODEL DEBE definirse antes de la primera migracion.
# Cambiarlo despues es extremadamente costoso. Siempre usar un modelo custom.
AUTH_USER_MODEL = 'usuarios.Usuario'

# ===========================================================================
# Validadores de contrasena
# ===========================================================================

# Decision de seguridad: Politica de contrasenas estricta para reducir la
# superficie de ataque ante ataques de diccionario y fuerza bruta.
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        # Minimo 10 caracteres. Mas que el default (8) para mayor seguridad.
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ===========================================================================
# Django REST Framework
# ===========================================================================

REST_FRAMEWORK = {
    # Autenticacion por defecto: JWT
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Solo usuarios autenticados pueden acceder a cualquier endpoint por defecto
    # Se puede sobrescribir por vista con permission_classes = [AllowAny]
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # Renderizadores: solo JSON en produccion, con BrowsableAPI en desarrollo
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    # Paginacion global para todos los ListAPIView
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.PaginacionEstandar',
    'PAGE_SIZE': 20,
    # Filtrado con django-filter
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    # Manejador de excepciones personalizado para respuestas estandarizadas
    'EXCEPTION_HANDLER': 'config.exceptions.manejador_de_excepciones',
    # Formatos de fecha y hora aceptados (flexibilidad para ingreso de usuarios)
    'DATETIME_INPUT_FORMATS': (
        'iso-8601',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y',
    ),
}

# ===========================================================================
# Configuracion de JWT (djangorestframework-simplejwt)
# ===========================================================================

from datetime import timedelta

SIMPLE_JWT = {
    # Token de acceso con vida util corta por seguridad
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    # Token de refresco con vida util larga
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    # Rotar el refresh token en cada uso (invalida el anterior)
    'ROTATE_REFRESH_TOKENS': True,
    # Anadir el refresh usado a la lista negra (requiere token_blacklist)
    'BLACKLIST_AFTER_ROTATION': True,
    # Algoritmo de firma del token
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    # El tipo de token que se usa en el header Authorization
    'AUTH_HEADER_TYPES': ('Bearer',),
    # Incluir informacion del usuario en el token para evitar consultas
    # innecesarias a la base de datos en cada request
    'TOKEN_OBTAIN_SERIALIZER': 'apps.usuarios.serializers.TokenPersonalizadoObtainSerializer',
}

# ===========================================================================
# Internacionalizacion
# ===========================================================================

LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True

# ===========================================================================
# Archivos estaticos
# ===========================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise comprime y cachea los archivos estaticos automaticamente
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ===========================================================================
# Tipo de clave primaria por defecto
# ===========================================================================

# Decision: BigAutoField como default para escalar sin problemas a millones
# de registros. El AutoField (int de 32 bits) se agota en ~2.1 mil millones.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
