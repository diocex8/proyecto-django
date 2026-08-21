"""
apps/inscripciones/views.py

Vistas del dominio de inscripciones.

Decision: Se usa GenericAPIView con mixins en lugar de ModelViewSet porque
las inscripciones no tienen un CRUD completo:
- No hay PUT/PATCH (una inscripcion no se "edita", se retira).
- El "DELETE" es logico (cambia estado a RETIRADA, no elimina el registro).
"""

import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.permissions import EsEstudiante, EsPropietarioDeLaInscripcion
from .models import Inscripcion
from .serializers import InscripcionListaSerializer, InscripcionCrearSerializer

logger = logging.getLogger('gestion_academica')


class InscripcionListaCrearView(generics.ListCreateAPIView):
    """
    GET  /api/v1/inscripciones/  -> Lista las inscripciones del estudiante autenticado.
    POST /api/v1/inscripciones/  -> Inscribe al estudiante en un curso.
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), EsEstudiante()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InscripcionCrearSerializer
        return InscripcionListaSerializer

    def get_queryset(self):
        """
        Un estudiante ve solo sus inscripciones.
        Un profesor ve las inscripciones de sus cursos.
        Un administrador ve todas.

        OPTIMIZACION: select_related carga curso y estudiante en una sola SQL.
        prefetch_related carga el profesor del curso evitando N+1 adicional.
        """
        usuario = self.request.user

        base_qs = Inscripcion.objects.select_related(
            'curso', 'curso__profesor', 'estudiante'
        )

        if usuario.es_estudiante:
            return base_qs.filter(estudiante=usuario)
        elif usuario.es_profesor:
            return base_qs.filter(curso__profesor=usuario)
        elif usuario.es_administrador:
            return base_qs

        return Inscripcion.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inscripcion = serializer.save()
        return Response(
            {
                'exito': True,
                'mensaje': f'Inscripcion exitosa en el curso "{inscripcion.curso.nombre}".',
                'inscripcion_id': inscripcion.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class InscripcionDetalleRetirarView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/v1/inscripciones/{id}/  -> Ver detalle de una inscripcion.
    DELETE /api/v1/inscripciones/{id}/  -> Retirarse del curso (soft-delete logico).
    """
    serializer_class = InscripcionListaSerializer
    permission_classes = [IsAuthenticated, EsPropietarioDeLaInscripcion]

    def get_queryset(self):
        return Inscripcion.objects.select_related(
            'curso', 'curso__profesor', 'estudiante'
        )

    def destroy(self, request, *args, **kwargs):
        """
        Sobreescribimos destroy para implementar un soft-delete logico.
        En lugar de eliminar el registro, cambiamos el estado a RETIRADA.
        Esto preserva el historial academico del estudiante.
        """
        inscripcion = self.get_object()

        if inscripcion.estado != Inscripcion.Estado.ACTIVA:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f'No puedes retirarte de esta inscripcion. '
                f'Estado actual: {inscripcion.get_estado_display()}.'
            )

        inscripcion.retirar()
        return Response(
            {
                'exito': True,
                'mensaje': f'Te has retirado exitosamente del curso "{inscripcion.curso.nombre}".',
            },
            status=status.HTTP_200_OK,
        )
