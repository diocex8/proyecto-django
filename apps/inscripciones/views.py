"""
apps/inscripciones/views.py

Vistas del dominio de inscripciones.
"""

import logging

from django.utils.safestring import mark_safe
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.permissions import EsPropietarioDeLaInscripcion
from .models import Inscripcion
from .serializers import (
    InscripcionListaSerializer,
    InscripcionDetalleSerializer,
    InscripcionCrearSerializer,
    InscripcionModificarSerializer,
)

logger = logging.getLogger('gestion_academica')


class InscripcionListaCrearView(generics.ListCreateAPIView):
    """
    GET  /api/v1/inscripciones/  -> Lista y filtra inscripciones.
    POST /api/v1/inscripciones/  -> Inscribe un estudiante en un curso.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['curso', 'estado', 'estudiante']
    search_fields = [
        'estudiante__first_name',
        'estudiante__last_name',
        'estudiante__email',
        'estudiante__username',
        'curso__nombre',
        'curso__codigo',
    ]
    ordering_fields = ['fecha_inscripcion', 'nota_final', 'estado']
    ordering = ['-fecha_inscripcion']

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InscripcionCrearSerializer
        return InscripcionListaSerializer

    def get_view_description(self, html=False):
        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)

        if user and user.is_authenticated and (user.es_profesor or user.es_administrador):
            from apps.cursos.models import Curso
            if user.es_profesor:
                cursos = Curso.objects.filter(profesor=user).order_by('nombre')
            else:
                cursos = Curso.objects.all().order_by('nombre')

            buttons_html = '<div style="margin: 8px 0; display: flex; flex-wrap: wrap; gap: 8px;">'
            buttons_html += '<a href="/api/v1/inscripciones/" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Todas las Inscripciones</a>'
            for c in cursos:
                buttons_html += f'<a href="/api/v1/inscripciones/?curso={c.id}" style="background: #2563eb; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Curso {c.codigo}: {c.nombre}</a>'
            buttons_html += '</div>'
            
            search_html = """
            <div style="margin: 16px 0; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <form method="GET" action="/api/v1/inscripciones/" style="display: flex; gap: 8px;">
                    <input type="text" name="search" placeholder="Buscar estudiante por nombre, correo o usuario..." style="flex: 1; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                    <button type="submit" style="background: #10b981; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600;">Buscar</button>
                </form>
            </div>
            """

            return mark_safe(buttons_html + search_html) if html else "Inscripciones"

        return ""

    def get_queryset(self):
        """
        Un estudiante ve solo sus inscripciones.
        Un profesor ve las inscripciones de sus cursos.
        Un administrador ve todas.
        """
        usuario = self.request.user

        base_qs = Inscripcion.objects.select_related(
            'curso', 'curso__profesor', 'estudiante'
        )

        if getattr(usuario, 'es_estudiante', False):
            return base_qs.filter(estudiante=usuario)
        elif getattr(usuario, 'es_profesor', False):
            return base_qs.filter(curso__profesor=usuario)
        elif getattr(usuario, 'es_administrador', False):
            return base_qs

        return Inscripcion.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inscripcion = serializer.save()
        estudiante_nombre = inscripcion.estudiante.get_full_name() or inscripcion.estudiante.username

        if inscripcion.estado == Inscripcion.Estado.PENDIENTE:
            mensaje = f'Solicitud de inscripcion enviada exitosamente para el curso "{inscripcion.curso.nombre}". Debes esperar la aceptacion del profesor.'
        else:
            mensaje = f'Estudiante "{estudiante_nombre}" inscrito exitosamente en el curso "{inscripcion.curso.nombre}".'

        return Response(
            {
                'exito': True,
                'mensaje': mensaje,
                'inscripcion_id': inscripcion.pk,
                'estado': inscripcion.estado,
                'estado_display': inscripcion.get_estado_display(),
            },
            status=status.HTTP_201_CREATED,
        )


class InscripcionDetalleRetirarView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/inscripciones/{id}/  -> Ver detalle de una inscripcion y promedios.
    PUT/PATCH /api/v1/inscripciones/{id}/ -> Modificar estado y nota final (Profesores/Admins).
    DELETE /api/v1/inscripciones/{id}/  -> Desinscribir/Retirar al estudiante (soft-delete).
    """
    permission_classes = [IsAuthenticated, EsPropietarioDeLaInscripcion]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return InscripcionModificarSerializer
        return InscripcionDetalleSerializer

    def get_queryset(self):
        return Inscripcion.objects.select_related(
            'curso', 'curso__profesor', 'estudiante'
        )

    def get_view_description(self, html=False):
        inscripcion = None
        try:
            inscripcion = self.get_object()
        except Exception:
            pass

        if inscripcion:
            est = inscripcion.estudiante
            stats = inscripcion.calcular_estadisticas_academicas()
            rendimiento = stats['estado_rendimiento']
            badge_color = "#16a34a" if "Aprobando" in rendimiento and "riesgo" not in rendimiento else ("#d97706" if "riesgo" in rendimiento else "#dc2626")

            estado_badge_color = "#d97706" if inscripcion.estado == Inscripcion.Estado.PENDIENTE else ("#16a34a" if inscripcion.estado == Inscripcion.Estado.ACTIVA else "#dc2626")

            botones_solicitud = ""
            if inscripcion.estado == Inscripcion.Estado.PENDIENTE:
                user = getattr(self, 'request', None) and getattr(self.request, 'user', None)
                if user and (user.es_administrador or (user.es_profesor and inscripcion.curso.profesor == user)):
                    botones_solicitud = (
                        f'<div style="margin-top: 12px; margin-bottom: 12px; display: flex; gap: 8px;">'
                        f'<a href="/api/v1/inscripciones/{inscripcion.id}/aprobar/" style="background: #16a34a; color: #ffffff; padding: 7px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600;">Aceptar Solicitud</a>'
                        f'<a href="/api/v1/inscripciones/{inscripcion.id}/rechazar/" style="background: #dc2626; color: #ffffff; padding: 7px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600;">Rechazar Solicitud</a>'
                        f'</div>'
                    )

            card = (
                f'<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
                f'<h3 style="margin: 0; color: #0f172a;">Estudiante: {est.get_full_name() or est.username} ({est.email})</h3>'
                f'<div>'
                f'<span style="background: {estado_badge_color}; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-right: 6px;">{inscripcion.get_estado_display()}</span>'
                f'<span style="background: {badge_color}; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold;">{rendimiento}</span>'
                f'</div>'
                f'</div>'
                f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; font-size: 13px; color: #334155; margin-bottom: 14px; background: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #cbd5e1;">'
                f'<div><strong>Curso:</strong> {inscripcion.curso.nombre} ({inscripcion.curso.codigo})</div>'
                f'<div><strong>Asignaciones Planificadas:</strong> {stats["total_asignaciones_planificadas"]}</div>'
                f'<div><strong>Asignaciones Publicadas:</strong> {stats["asignaciones_publicadas"]}</div>'
                f'<div><strong>Entregas Enviadas:</strong> {stats["entregas_enviadas"]} / {stats["total_asignaciones_planificadas"]} ({stats["porcentaje_avance"]})</div>'
                f'<div><strong>Evaluaciones Calificadas:</strong> {stats["entregas_calificadas"]}</div>'
                f'<div><strong>Promedio Evaluaciones (0-20):</strong> <span style="font-weight: bold; color: #2563eb;">{stats["promedio_acumulado_base20"] or "Sin calificar"}</span></div>'
                f'<div><strong>Nota Proyectada Curso (0-20):</strong> <span style="font-weight: bold; color: #0f172a;">{stats["nota_proyectada_curso"]}</span></div>'
                f'<div><strong>Nota Final Asignada:</strong> <span style="font-weight: bold; color: #16a34a;">{inscripcion.nota_final or "Pendiente"}</span></div>'
                f'<div><strong>Estado Inscripcion:</strong> {inscripcion.get_estado_display()}</div>'
                f'</div>'
                f'{botones_solicitud}'
                f'<a href="/api/v1/inscripciones/" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">&larr; Volver a la Lista de Inscripciones</a>'
                f'</div>'
            )
            return mark_safe(card) if html else "Detalle de Inscripcion"

        return ""

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'exito': True,
            'mensaje': 'Inscripcion actualizada exitosamente.',
            'inscripcion': serializer.data,
        })

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete logico: cambia el estado a RETIRADA.
        Permite a estudiantes retirarse a si mismos, y a profesores/admins desinscribir estudiantes.
        """
        inscripcion = self.get_object()

        if inscripcion.estado == Inscripcion.Estado.RETIRADA:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'El estudiante ya se encuentra retirado de este curso.'
            )

        inscripcion.retirar()
        estudiante_nombre = inscripcion.estudiante.get_full_name() or inscripcion.estudiante.username
        return Response(
            {
                'exito': True,
                'mensaje': f'El estudiante "{estudiante_nombre}" ha sido desinscrito (retirado) del curso "{inscripcion.curso.nombre}".',
            },
            status=status.HTTP_200_OK,
        )


class AprobarInscripcionView(generics.GenericAPIView):
    """
    POST/GET /api/v1/inscripciones/{id}/aprobar/
    Permite al profesor propietario o administrador aprobar y activar una inscripcion.
    """
    permission_classes = [IsAuthenticated, EsPropietarioDeLaInscripcion]
    queryset = Inscripcion.objects.select_related('curso', 'estudiante')

    def post(self, request, pk):
        inscripcion = self.get_object()
        if not (request.user.es_administrador or (request.user.es_profesor and inscripcion.curso.profesor == request.user)):
            return Response({'error': 'No tienes permisos para aprobar esta inscripcion.'}, status=status.HTTP_403_FORBIDDEN)

        inscripcion.activar()
        estudiante_nombre = inscripcion.estudiante.get_full_name() or inscripcion.estudiante.username
        return Response({
            'exito': True,
            'mensaje': f'Inscripcion del estudiante "{estudiante_nombre}" en el curso "{inscripcion.curso.nombre}" aprobada y activada exitosamente.',
            'estado': inscripcion.estado,
            'estado_display': inscripcion.get_estado_display(),
        })

    def get(self, request, pk):
        return self.post(request, pk)


class RechazarInscripcionView(generics.GenericAPIView):
    """
    POST/GET /api/v1/inscripciones/{id}/rechazar/
    Permite al profesor propietario o administrador rechazar una solicitud de inscripcion.
    """
    permission_classes = [IsAuthenticated, EsPropietarioDeLaInscripcion]
    queryset = Inscripcion.objects.select_related('curso', 'estudiante')

    def post(self, request, pk):
        inscripcion = self.get_object()
        if not (request.user.es_administrador or (request.user.es_profesor and inscripcion.curso.profesor == request.user)):
            return Response({'error': 'No tienes permisos para rechazar esta inscripcion.'}, status=status.HTTP_403_FORBIDDEN)

        inscripcion.rechazar()
        estudiante_nombre = inscripcion.estudiante.get_full_name() or inscripcion.estudiante.username
        return Response({
            'exito': True,
            'mensaje': f'Solicitud de inscripcion del estudiante "{estudiante_nombre}" para el curso "{inscripcion.curso.nombre}" ha sido rechazada.',
            'estado': inscripcion.estado,
            'estado_display': inscripcion.get_estado_display(),
        })

    def get(self, request, pk):
        return self.post(request, pk)
