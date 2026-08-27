"""
apps/inscripciones/urls.py

Enrutamiento del dominio de inscripciones.
"""

from django.urls import path
from .views import (
    InscripcionListaCrearView,
    InscripcionDetalleRetirarView,
    AprobarInscripcionView,
    RechazarInscripcionView,
)

urlpatterns = [
    path('', InscripcionListaCrearView.as_view(), name='inscripcion-lista-crear'),
    path('<int:pk>/', InscripcionDetalleRetirarView.as_view(), name='inscripcion-detalle'),
    path('<int:pk>/aprobar/', AprobarInscripcionView.as_view(), name='inscripcion-aprobar'),
    path('<int:pk>/rechazar/', RechazarInscripcionView.as_view(), name='inscripcion-rechazar'),
]
