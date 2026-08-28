"""
apps/asignaciones/urls.py

Enrutamiento del dominio de asignaciones y entregas.

Los endpoints de entrega estan anidados bajo asignaciones:
    /api/v1/asignaciones/
    /api/v1/asignaciones/{id}/
    /api/v1/asignaciones/{id}/entregas/
    /api/v1/asignaciones/{id}/entregas/{pk}/
    /api/v1/asignaciones/{id}/entregas/{pk}/calificar/
"""

from django.urls import path
from .views import (
    AsignacionListaCrearView,
    AsignacionDetalleActualizarView,
    EntregaListaCrearView,
    EntregaDetalleView,
    CalificarEntregaView,
    CalificarEstudianteAsignacionView,
)

urlpatterns = [
    # Asignaciones
    path('', AsignacionListaCrearView.as_view(), name='asignacion-lista-crear'),
    path('<int:pk>/', AsignacionDetalleActualizarView.as_view(), name='asignacion-detalle'),

    # Entregas anidadas bajo una asignacion
    path(
        '<int:asignacion_id>/entregas/',
        EntregaListaCrearView.as_view(),
        name='entrega-lista-crear',
    ),
    path(
        '<int:asignacion_id>/entregas/<int:pk>/',
        EntregaDetalleView.as_view(),
        name='entrega-detalle',
    ),
    path(
        '<int:asignacion_id>/entregas/<int:pk>/calificar/',
        CalificarEntregaView.as_view(),
        name='entrega-calificar',
    ),
    path(
        '<int:asignacion_id>/estudiantes/<int:estudiante_id>/calificar/',
        CalificarEstudianteAsignacionView.as_view(),
        name='asignacion-calificar-estudiante',
    ),
]
