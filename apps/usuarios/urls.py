"""
Enrutamiento del dominio de usuarios y autenticacion.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView

from .views import (
    LoginView,
    RefrescarTokenView,
    RegistroView,
    PerfilView,
    CambiarPasswordView,
    SolicitudProfesorViewSet,
)

app_name = 'usuarios'

router = DefaultRouter()
router.register(r'solicitudes', SolicitudProfesorViewSet, basename='solicitud')

urlpatterns = [
    # Autenticacion JWT
    path('token/', LoginView.as_view(), name='token-obtener'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', RefrescarTokenView.as_view(), name='token-refrescar'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token-blacklist'),

    # Registro y perfil
    path('registro/', RegistroView.as_view(), name='registro'),
    path('perfil/', PerfilView.as_view(), name='perfil-usuario'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar-password'),

    # Solicitudes de profesores (solo admin)
    path('', include(router.urls)),
]

