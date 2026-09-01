"""
Vistas del dominio de usuarios.
"""

import logging

from django.db import models
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    TokenPersonalizadoObtainSerializer,
    UsuarioDetalleSerializer,
    RegistroUsuarioSerializer,
    ActualizarPerfilSerializer,
    CambiarPasswordSerializer,
    SolicitudProfesorListaSerializer,
    RechazarSolicitudSerializer,
)
from .permissions import EsAdministrador
from .services import obtener_estadisticas_estudiante, obtener_estadisticas_profesor

logger = logging.getLogger('gestion_academica')


class LoginView(TokenObtainPairView):
    """
    Endpoint de autenticacion. Devuelve par de tokens JWT.
    POST /api/v1/auth/token/
    """
    serializer_class = TokenPersonalizadoObtainSerializer
    permission_classes = [AllowAny]


class RefrescarTokenView(TokenRefreshView):
    """
    Endpoint para renovar el token de acceso usando el refresh token.
    POST /api/v1/auth/token/refresh/
    """
    permission_classes = [AllowAny]


class RegistroView(generics.CreateAPIView):
    """
    Endpoint de registro de nuevos usuarios.
    POST /api/v1/auth/registro/
    """
    serializer_class = RegistroUsuarioSerializer
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """
        Permite visualizar instrucciones y el formulario de registro en el navegador.
        """
        return Response({
            'mensaje': 'Completa el formulario inferior para registrar un nuevo usuario (estudiante o profesor).',
            'roles_disponibles': ['estudiante', 'profesor'],
            'ejemplo_cuerpo': {
                'email': 'usuario@correo.com',
                'username': 'usuario1',
                'password': 'Password123!',
                'first_name': 'Nombre',
                'last_name': 'Apellido',
                'rol': 'estudiante'
            }
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()

        if usuario.es_profesor:
            mensaje = (
                'Registro recibido exitosamente. Tu cuenta de profesor esta pendiente de '
                'aprobacion por un administrador antes de poder iniciar sesion.'
            )
        else:
            mensaje = 'Usuario registrado exitosamente. Ya puedes iniciar sesion.'

        return Response(
            {
                'exito': True,
                'mensaje': mensaje,
                'usuario': {
                    'id': usuario.pk,
                    'email': usuario.email,
                    'rol': usuario.rol,
                    'activo': usuario.is_active,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class PerfilView(generics.RetrieveUpdateAPIView):
    """
    Endpoint para ver y actualizar el perfil del usuario autenticado.
    GET  /api/v1/auth/perfil/
    PATCH /api/v1/auth/perfil/
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Patron de serializer dinamico segun el metodo HTTP:
        - GET: Serializador de lectura (datos completos, campos calculados).
        - PATCH/PUT: Serializador de escritura (solo campos modificables).
        """
        if self.request.method in ('PUT', 'PATCH'):
            return ActualizarPerfilSerializer
        return UsuarioDetalleSerializer

    def get_object(self):
        """Retorna siempre el usuario autenticado. No hay parametro de ID."""
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        usuario = self.get_object()
        serializer = self.get_serializer(usuario)
        data = serializer.data

        # Agregar estadisticas desde la capa de servicio
        if usuario.es_estudiante:
            data['estadisticas'] = obtener_estadisticas_estudiante(usuario)
        elif usuario.es_profesor:
            data['estadisticas'] = obtener_estadisticas_profesor(usuario)

        return Response({'exito': True, 'datos': data})


class CambiarPasswordView(APIView):
    """
    Endpoint para cambiar la contrasena del usuario autenticado.
    POST /api/v1/auth/cambiar-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambiarPasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'exito': True,
                'mensaje': 'Contrasena actualizada exitosamente. Vuelve a iniciar sesion.',
            },
            status=status.HTTP_200_OK,
        )


class SolicitudProfesorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para que los administradores gestionen las solicitudes de profesores.
    GET /api/v1/auth/solicitudes/
    """
    serializer_class = SolicitudProfesorListaSerializer
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get_queryset(self):
        # Muestra todas las solicitudes (pendientes primero)
        from .models import SolicitudProfesor
        return SolicitudProfesor.objects.all().select_related('usuario').order_by(
            models.Case(
                models.When(estado=SolicitudProfesor.Estado.PENDIENTE, then=0),
                default=1
            ),
            '-fecha_solicitud'
        )

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.estado != solicitud.Estado.PENDIENTE:
            return Response(
                {'detail': 'Solo se pueden aprobar solicitudes pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        solicitud.aceptar()
        return Response({'detail': f'Solicitud de {solicitud.email} aprobada. Cuenta activada.'})

    @action(detail=True, methods=['post'], serializer_class=RechazarSolicitudSerializer)
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.estado != solicitud.Estado.PENDIENTE:
            return Response(
                {'detail': 'Solo se pueden rechazar solicitudes pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        motivo = serializer.validated_data['motivo']
        
        solicitud.rechazar(motivo)
        return Response({'detail': 'Solicitud rechazada. Usuario bloqueado por 2 horas.'})
