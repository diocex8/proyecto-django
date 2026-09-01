from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CursoViewSet, CursoPendienteViewSet

router = DefaultRouter()
router.register(r'', CursoViewSet, basename='curso')

pendiente_router = DefaultRouter()
pendiente_router.register(r'', CursoPendienteViewSet, basename='curso-pendiente')

urlpatterns = [
    path('', include(router.urls)),
]
