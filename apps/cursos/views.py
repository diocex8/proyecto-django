"""
Vistas del dominio de los cursos
"""

import logging

from django.db.models import Count, Q, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inscripciones.models import Inscripcion
from apps.usuarios.permissions import (
    EsProfesor,
    EsProfesorOSoloLectura,
    EsPropietarioDelCurso,
    EsEstudianteInscritoOProfesorPropietario,
)
from .models import Curso
from .serializers import (
    CursoListaSerializer,
    CursoDetalleSerializer,
    CursoCrearActualizarSerializer,
    CambiarEstadoCursoSerializer,
)

logger = logging.getLogger('gestion_academica')


class CursoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el CRUD completo de Cursos.

    Endpoints generados automaticamente por ModelViewSet:
        GET    /api/v1/cursos/          -> list()
        POST   /api/v1/cursos/          -> create()
        GET    /api/v1/cursos/{id}/     -> retrieve()
        PUT    /api/v1/cursos/{id}/     -> update()
        PATCH  /api/v1/cursos/{id}/     -> partial_update()
        DELETE /api/v1/cursos/{id}/     -> destroy()

    Endpoints adicionales (@action):
        POST   /api/v1/cursos/{id}/cambiar-estado/   -> cambiar_estado()
        GET    /api/v1/cursos/{id}/asignaciones/      -> listar_asignaciones()
        GET    /api/v1/cursos/{id}/inscripciones/     -> listar_inscripciones()
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'profesor']
    search_fields = ['nombre', 'codigo', 'descripcion']
    ordering_fields = ['fecha_creacion', 'nombre', 'fecha_inicio']
    ordering = ['-fecha_creacion']

    def get_permissions(self):
        """
        Permisos dinamicos segun la accion.
        """
        if self.action in ('list', 'retrieve'):
            permisos = [IsAuthenticated]
        elif self.action == 'create':
            permisos = [IsAuthenticated, EsProfesor]
        else:
            # update, partial_update, destroy, cambiar_estado
            permisos = [IsAuthenticated, EsProfesor, EsPropietarioDelCurso]
        return [permiso() for permiso in permisos]

    def get_serializer_class(self):
        """Serializer dinamico segun la accion."""
        if self.action == 'list':
            return CursoListaSerializer
        elif self.action in ('create', 'update', 'partial_update'):
            return CursoCrearActualizarSerializer
        elif self.action == 'cambiar_estado':
            return CambiarEstadoCursoSerializer
        return CursoDetalleSerializer

    def get_queryset(self):
        """
        Queryset base con todas las optimizaciones aplicadas.

        select_related('profesor'): carga el usuario profesor en la misma
        consulta SQL usando JOIN, evitando una consulta por curso.

        annotate(...): agrega columnas calculadas a cada fila de la consulta,
        evitando iterar en Python o hacer subconsultas por cada objeto.

        El resultado: una sola consulta SQL eficiente para toda la lista.
        """
        usuario = self.request.user

        queryset = Curso.objects.select_related('profesor').annotate(
            total_inscritos_anotado=Count(
                'inscripciones',
                filter=Q(inscripciones__estado=Inscripcion.Estado.ACTIVA),
                distinct=True,
            ),
            total_asignaciones_anotado=Count('asignaciones', distinct=True),
        )

        # Filtrar segun el rol del usuario
        if usuario.es_estudiante:
            # El estudiante ve solo cursos publicados
            return queryset.filter(estado=Curso.Estado.PUBLICADO)
        elif usuario.es_administrador:
            # El administrador ve todos los cursos en cualquier estado
            return queryset
        elif usuario.es_profesor:
            # El profesor ve sus propios cursos (en cualquier estado)
            return queryset.filter(profesor=usuario)

        return queryset.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.esta_bloqueado:
            from django.utils.timezone import localtime
            return Response(
                {"detail": f"Tu cuenta esta bloqueada temporalmente por intentos excesivos de creacion de cursos. Vuelve a intentar despues de {localtime(user.bloqueado_hasta).strftime('%H:%M')}."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar cooldown
        from datetime import timedelta
        from django.utils import timezone
        hace_una_hora = timezone.now() - timedelta(hours=1)
        cursos_recientes = Curso.objects.filter(profesor=user, fecha_creacion__gte=hace_una_hora).count()
        
        if cursos_recientes >= 3:
            user.intentos_fallidos_creacion += 1
            if user.intentos_fallidos_creacion >= 3:
                user.bloqueado_hasta = timezone.now() + timedelta(minutes=30)
                user.intentos_fallidos_creacion = 0
                user.save(update_fields=['bloqueado_hasta', 'intentos_fallidos_creacion'])
                return Response(
                    {"detail": "Has insistido demasiado. Tu cuenta ha sido bloqueada por 30 minutos."},
                    status=status.HTTP_403_FORBIDDEN
                )
            user.save(update_fields=['intentos_fallidos_creacion'])
            return Response(
                {"detail": f"Has alcanzado el limite de creacion de cursos (3 por hora). Intento fallido {user.intentos_fallidos_creacion}/3 antes de bloqueo."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED and user.intentos_fallidos_creacion > 0:
            user.intentos_fallidos_creacion = 0
            user.save(update_fields=['intentos_fallidos_creacion'])
        return response

    def perform_create(self, serializer):
        """El profesor se asigna en el serializer desde request.user y nace en estado PENDIENTE."""
        curso = serializer.save(estado=Curso.Estado.PENDIENTE)
        logger.info(
            'Curso creado en estado PENDIENTE. ID: %s, Codigo: %s, Profesor: %s',
            curso.pk, curso.codigo, self.request.user.email,
        )

    def perform_destroy(self, instance):
        """
        Sobreescribimos destroy para validar que el curso no tenga
        inscripciones activas antes de eliminarlo.
        """
        if instance.inscripciones.filter(estado=Inscripcion.Estado.ACTIVA).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'No se puede eliminar un curso con inscripciones activas. '
                'Archiva el curso en su lugar.'
            )
        logger.info('Curso eliminado. ID: %s, Codigo: %s', instance.pk, instance.codigo)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Accion personalizada para cambiar el estado del curso.
        POST /api/v1/cursos/{id}/cambiar-estado/
        """
        curso = self.get_object()
        serializer = CambiarEstadoCursoSerializer(
            data=request.data,
            context={'curso': curso},
        )
        serializer.is_valid(raise_exception=True)

        nuevo_estado = serializer.validated_data['nuevo_estado']

        if nuevo_estado == Curso.Estado.PUBLICADO:
            curso.publicar()
        elif nuevo_estado == Curso.Estado.ARCHIVADO:
            curso.archivar()
        else:
            curso.estado = nuevo_estado
            curso.save(update_fields=['estado', 'fecha_actualizacion'])

        return Response(
            {
                'exito': True,
                'mensaje': f'Estado del curso actualizado a "{curso.get_estado_display()}".',
                'estado': curso.estado,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='asignaciones')
    def listar_asignaciones(self, request, pk=None):
        """
        Lista las asignaciones de este curso.
        - Estudiantes: deben estar inscritos activamente para verlas.
        - Profesores: deben ser el profesor propietario del curso.

        Para entregar una asignacion:
        POST /api/v1/asignaciones/{id_asignacion}/entregas/
        Body: {"contenido": "Texto de la entrega o respuesta"}
        """
        curso = self.get_object()

        # Validacion de permisos segun rol
        if request.user.es_estudiante:
            esta_inscrito = Inscripcion.objects.filter(
                curso=curso,
                estudiante=request.user,
                estado=Inscripcion.Estado.ACTIVA,
            ).exists()
            if not esta_inscrito:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    'Debes estar inscrito activamente en el curso para ver sus asignaciones.'
                )
        elif request.user.es_profesor and not request.user.es_administrador and curso.profesor != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'Solo el profesor propietario o un administrador puede ver las asignaciones de este curso.'
            )

        from apps.asignaciones.models import Asignacion
        from apps.asignaciones.serializers import AsignacionListaSerializer
        from config.pagination import PaginacionEstandar

        asignaciones = Asignacion.objects.filter(curso=curso).annotate(
            total_entregas_anotado=Count('entregas', distinct=True)
        ).order_by('fecha_entrega')

        paginator = PaginacionEstandar()
        pagina = paginator.paginate_queryset(asignaciones, request)
        serializer = AsignacionListaSerializer(pagina, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_view_description(self, html=False):
        if not html:
            return "Cursos"

        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)
        if not (user and user.is_authenticated and (user.es_profesor or user.es_administrador)):
            return ""

        from django.utils.safestring import mark_safe
        from apps.inscripciones.models import Inscripcion

        # Si esta en la vista de detalle de un curso
        curso = None
        if hasattr(self, 'get_object'):
            try:
                curso = self.get_object()
            except Exception:
                pass

        if curso:
            solicitudes = Inscripcion.objects.filter(
                curso=curso,
                estado=Inscripcion.Estado.PENDIENTE
            ).select_related('estudiante').order_by('-fecha_inscripcion')
            titulo = f'Solicitudes Pendientes para {curso.nombre} ({solicitudes.count()})'
        else:
            if user.es_profesor and not user.es_administrador:
                solicitudes = Inscripcion.objects.filter(
                    curso__profesor=user,
                    estado=Inscripcion.Estado.PENDIENTE
                ).select_related('curso', 'estudiante').order_by('-fecha_inscripcion')
            else:
                solicitudes = Inscripcion.objects.filter(
                    estado=Inscripcion.Estado.PENDIENTE
                ).select_related('curso', 'estudiante').order_by('-fecha_inscripcion')
            titulo = f'Solicitudes de Inscripcion Pendientes en tus Cursos ({solicitudes.count()})'

        total = solicitudes.count()
        if total == 0:
            html_out = '<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; margin-bottom: 14px; font-size: 13px; color: #475569;">'
            html_out += '<strong>Solicitudes de Inscripcion:</strong> No hay solicitudes pendientes por revisar.'
            html_out += '</div>'
            return mark_safe(html_out)

        html_out = f'<div style="background: #fefce8; border: 1px solid #fef08a; padding: 14px; border-radius: 8px; margin-bottom: 16px;">'
        html_out += f'<h4 style="margin: 0 0 10px 0; color: #854d0e; font-size: 14px; font-weight: 700;">{titulo}</h4>'
        html_out += '<div style="display: flex; flex-direction: column; gap: 8px;">'
        for sol in solicitudes[:10]:
            est_nom = sol.estudiante.get_full_name() or sol.estudiante.username
            html_out += f'<div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 8px 12px; border-radius: 6px; border: 1px solid #fde047; font-size: 13px;">'
            html_out += f'<div><strong>{est_nom}</strong> ({sol.estudiante.email}) &rarr; <em>{sol.curso.nombre}</em></div>'
            html_out += f'<div style="display: flex; gap: 6px;">'
            html_out += f'<a href="/api/v1/inscripciones/{sol.id}/aprobar/" style="background: #16a34a; color: #ffffff; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: 600;">Aceptar</a>'
            html_out += f'<a href="/api/v1/inscripciones/{sol.id}/rechazar/" style="background: #dc2626; color: #ffffff; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: 600;">Rechazar</a>'
            html_out += f'</div></div>'
        html_out += '</div></div>'
        return mark_safe(html_out)

    @action(detail=True, methods=['get'], url_path='solicitudes')
    def listar_solicitudes(self, request, pk=None):
        """
        Lista las solicitudes pendientes de inscripcion para este curso.
        GET /api/v1/cursos/{id}/solicitudes/
        """
        curso = self.get_object()
        if not (request.user.es_administrador or (request.user.es_profesor and curso.profesor == request.user)):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Solo el profesor propietario o un administrador puede ver las solicitudes.')

        solicitudes = Inscripcion.objects.filter(
            curso=curso,
            estado=Inscripcion.Estado.PENDIENTE
        ).select_related('estudiante').order_by('-fecha_inscripcion')

        from apps.inscripciones.serializers import InscripcionListaSerializer
        from config.pagination import PaginacionInscripciones

        paginator = PaginacionInscripciones()
        pagina = paginator.paginate_queryset(solicitudes, request)
        serializer = InscripcionListaSerializer(pagina, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'], url_path='inscripciones')
    def listar_inscripciones(self, request, pk=None):
        """
        Lista las inscripciones del curso.
        Accesible por el profesor propietario o un administrador.
        GET /api/v1/cursos/{id}/inscripciones/
        """
        curso = self.get_object()

        if not (request.user.es_administrador or (request.user.es_profesor and curso.profesor == request.user)):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'Solo el profesor propietario o un administrador puede ver las inscripciones.'
            )

        inscripciones = Inscripcion.objects.filter(
            curso=curso
        ).select_related('estudiante').order_by('-fecha_inscripcion')

        from apps.inscripciones.serializers import InscripcionListaSerializer
        from config.pagination import PaginacionInscripciones

        paginator = PaginacionInscripciones()
        pagina = paginator.paginate_queryset(inscripciones, request)
        serializer = InscripcionListaSerializer(pagina, many=True)
        return paginator.get_paginated_response(serializer.data)
