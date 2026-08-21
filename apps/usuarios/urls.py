"""
apps/usuarios/urls.py

Enrutamiento del dominio de usuarios y autenticacion.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView

from .views import (
    LoginView,
    RefrescarTokenView,
    RegistroView,
    PerfilView,
    CambiarPasswordView,
)

urlpatterns = [
    # Autenticacion JWT
    path('token/', LoginView.as_view(), name='token-obtener'),
    path('token/refresh/', RefrescarTokenView.as_view(), name='token-refrescar'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token-blacklist'),

    # Registro y perfil
    path('registro/', RegistroView.as_view(), name='registro-usuario'),
    path('perfil/', PerfilView.as_view(), name='perfil-usuario'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar-password'),
]
