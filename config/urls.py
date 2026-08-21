"""
config/urls.py

Enrutador principal del proyecto.
Cada aplicacion registra sus propias URLs en su archivo urls.py
y aqui se incluyen con un prefijo semantico.

Versionado de API:
    Se usa el prefijo /api/v1/ para habilitar versionado semantico.
    Cuando sea necesario introducir cambios que rompan compatibilidad,
    se puede anadir /api/v2/ sin afectar a los clientes existentes.
"""

from django.contrib import admin
from django.urls import path, include

from config.views import IndexView

urlpatterns = [
    # Pagina de inicio (Dashboard)
    path('', IndexView.as_view(), name='index'),

    # Panel de administracion de Django
    path('admin/', admin.site.urls),

    # Endpoints de autenticacion JWT
    path('api/v1/auth/', include('apps.usuarios.urls')),

    # Endpoints de cursos
    path('api/v1/cursos/', include('apps.cursos.urls')),

    # Endpoints de inscripciones
    path('api/v1/inscripciones/', include('apps.inscripciones.urls')),

    # Endpoints de asignaciones y entregas
    path('api/v1/asignaciones/', include('apps.asignaciones.urls')),

    # Login/logout por sesion para la API navegable (solo desarrollo)
    # Habilita los botones "Log in" y "Log out" en el navegador.
    path('api-auth/', include('rest_framework.urls')),
]
