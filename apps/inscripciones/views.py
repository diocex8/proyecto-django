"""
apps/inscripciones/views.py

Vistas del dominio de inscripciones.

Decision: Se usa GenericAPIView con mixins en lugar de ModelViewSet porque
las inscripciones no tienen un CRUD completo:
- No hay PUT/PATCH (una inscripcion no se "edita", se retira).
- El "DELETE" es logico (cambia estado a RETIRADA, no elimina el registro).
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

            buttons_html = '<div style="margin: 12px 0; display: flex; flex-wrap: wrap; gap: 8px;">'
            buttons_html += '<a href="/api/v1/inscripciones/" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Todas las Inscripciones</a>'
            for c in cursos:
                buttons_html += f'<a href="/api/v1/inscripciones/?curso={c.id}" style="background: #2563eb; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Curso {c.codigo}: {c.nombre}</a>'
            buttons_html += '</div>'

            content = (
                '<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">'
                '<h3 style="margin-top: 0; color: #0f172a;">Gestion Academica y Busqueda de Inscripciones</h3>'
                '<p style="color: #475569; margin-bottom: 10px; font-size: 14px;">'
                '1. <strong>Sistema de Promedios Reales:</strong> Cada inscripcion calcula en tiempo real el porcentaje de avance, promedio de evaluaciones calificadas (base 20), nota proyectada segun las asignaciones planificadas y estado de rendimiento.<br>'
                '2. <strong>Buscar estudiante:</strong> Puedes usar el buscador o el parametro <code>?search=nombre_o_correo</code>.<br>'
                '3. <strong>Modificar / Desinscribir:</strong> Haz clic en el enlace <code>url_detalle</code> de cualquier inscripcion para ver su desglose academico, modificar estado, asignar nota final o retirarlo.<br>'
                '4. <strong>Inscripcion directa:</strong> Completa el formulario inferior para inscribir a un estudiante en tus cursos.'
                '</p>'
                '<h4 style="margin: 12px 0 6px 0; color: #1e293b;">Filtrar inscripciones por curso (Haz clic para filtrar):</h4>'
                f'{buttons_html}'
                '</div>'
            )
            return mark_safe(content) if html else "Gestion de Inscripciones"

        elif user and user.is_authenticated and getattr(user, 'es_estudiante', False):
            content = (
                '<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">'
                '<h3 style="margin-top: 0; color: #0f172a;">Mis Cursos, Promedios y Progreso Academico</h3>'
                '<p style="color: #475569; margin-bottom: 10px; font-size: 14px;">'
                '1. Revisa tu lista de cursos inscritos abajo junto con tu <strong>rendimiento academico</strong>, avance de asignaciones y promedios calculados.<br>'
                '2. Para inscribirte en un nuevo curso disponible, completa el formulario inferior seleccionando el <strong>Curso</strong>.<br>'
                '3. Para ver el detalle y desglose de un curso, accede a su <code>url_detalle</code>.'
                '</p>'
                '</div>'
            )
            return mark_safe(content) if html else "Mis Inscripciones"

        return mark_safe("<p>Inicia sesion para visualizar tus inscripciones.</p>") if html else "Inscripciones"

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
        return Response(
            {
                'exito': True,
                'mensaje': f'Estudiante "{estudiante_nombre}" inscrito exitosamente en el curso "{inscripcion.curso.nombre}".',
                'inscripcion_id': inscripcion.pk,
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
        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)
        inscripcion = None
        try:
            inscripcion = self.get_object()
        except Exception:
            pass

        info_header = ""
        if inscripcion:
            est = inscripcion.estudiante
            stats = inscripcion.calcular_estadisticas_academicas()
            rendimiento = stats['estado_rendimiento']
            badge_color = "#16a34a" if "Aprobando" in rendimiento and "riesgo" not in rendimiento else ("#d97706" if "riesgo" in rendimiento else "#dc2626")

            info_header = (
                f'<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
                f'<h3 style="margin: 0; color: #0f172a;">Estudiante: {est.get_full_name() or est.username} ({est.email})</h3>'
                f'<span style="background: {badge_color}; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold;">{rendimiento}</span>'
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
                f'<a href="/api/v1/inscripciones/" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">&larr; Volver a la Lista de Inscripciones</a>'
                f'</div>'
            )

        if user and user.is_authenticated and (user.es_profesor or user.es_administrador):
            content = (
                f'{info_header}'
                '<div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-bottom: 16px;">'
                '<h4 style="margin-top: 0; color: #1e293b;">Opciones de Gestion para Profesores y Administradores:</h4>'
                '<ul style="color: #475569; font-size: 13px; padding-left: 20px; line-height: 1.6;">'
                '<li><strong>Modificar Estado o Nota Final:</strong> Completa los campos en el formulario inferior (<code>estado</code>: <code>activa</code>, <code>retirada</code>, <code>completada</code>; <code>nota_final</code>: 0.00 a 20.00) y haz clic en <strong>PATCH</strong>.</li>'
                '<li><strong>Desinscribir al Estudiante:</strong> Haz clic en el boton rojo <strong>DELETE</strong> en la parte superior para retirar al estudiante de este curso.</li>'
                '</ul>'
                '</div>'
            )
            return mark_safe(content) if html else "Detalle y Modificacion de Inscripcion"

        elif user and user.is_authenticated and getattr(user, 'es_estudiante', False):
            content = (
                f'{info_header}'
                '<div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-bottom: 16px;">'
                '<h4 style="margin-top: 0; color: #1e293b;">Opciones de Estudiante:</h4>'
                '<p style="color: #475569; font-size: 13px;">'
                'Para retirarte voluntariamente de este curso, haz clic en el boton rojo <strong>DELETE</strong> en la parte superior.'
                '</p>'
                '</div>'
            )
            return mark_safe(content) if html else "Detalle de Inscripcion"

        return mark_safe("<p>Detalle de la inscripcion.</p>") if html else "Detalle"

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
