"""
apps/inscripciones/urls.py

Enrutamiento del dominio de inscripciones.
"""

from django.urls import path
from .views import InscripcionListaCrearView, InscripcionDetalleRetirarView

urlpatterns = [
    path('', InscripcionListaCrearView.as_view(), name='inscripcion-lista-crear'),
    path('<int:pk>/', InscripcionDetalleRetirarView.as_view(), name='inscripcion-detalle'),
]
