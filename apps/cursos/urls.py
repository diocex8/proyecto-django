"""
Enrutamiento del dominio de cursos usando DefaultRouter.

DefaultRouter genera automaticamente:
    /api/v1/cursos/           -> list, create
    /api/v1/cursos/{id}/      -> retrieve, update, partial_update, destroy
    /api/v1/cursos/{id}/cambiar-estado/ -> accion personalizada
    /api/v1/cursos/{id}/inscripciones/  -> accion personalizada
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CursoViewSet

router = DefaultRouter()
router.register(r'', CursoViewSet, basename='curso')

urlpatterns = [
    path('', include(router.urls)),
]
