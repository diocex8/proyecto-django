"""
apps/cursos/views.py

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

    def perform_create(self, serializer):
        """El profesor se asigna en el serializer desde request.user."""
        curso = serializer.save()
        logger.info(
            'Curso creado. ID: %s, Codigo: %s, Profesor: %s',
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
