from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CursoPendienteViewSet

router = DefaultRouter()
router.register(r'', CursoPendienteViewSet, basename='curso-pendiente')

urlpatterns = [
    path('', include(router.urls)),
]
