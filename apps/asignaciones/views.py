"""
apps/asignaciones/views.py

Vistas del dominio de asignaciones y entregas.

Los endpoints de Asignacion y Entrega estan anidados bajo Curso para
reflejar la jerarquia del dominio:
    /api/v1/asignaciones/                           -> Asignaciones (vista propia)
    /api/v1/asignaciones/{id}/entregas/             -> Entregas de una asignacion
    /api/v1/asignaciones/{id}/entregas/{eid}/calificar/ -> Calificar entrega
"""

import logging

from django.db.models import Count
from django.utils.safestring import mark_safe
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.permissions import (
    EsProfesor,
    EsEstudiante,
    EsPropietarioDeLaEntrega,
)
from apps.inscripciones.models import Inscripcion
from .models import Asignacion, Entrega
from .serializers import (
    AsignacionListaSerializer,
    AsignacionDetalleSerializer,
    AsignacionCrearActualizarSerializer,
    EntregaListaSerializer,
    EntregaDetalleSerializer,
    EntregaCrearSerializer,
    CalificarEntregaSerializer,
)

logger = logging.getLogger('gestion_academica')

class AsignacionListaCrearView(generics.ListCreateAPIView):
    """
    Listado y gestion de asignaciones del curso.
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo', 'permite_entrega_tardia']
    search_fields = ['titulo', 'descripcion', 'curso__nombre', 'curso__codigo']
    ordering_fields = ['fecha_entrega', 'porcentaje', 'valor_maximo', 'fecha_creacion']
    ordering = ['fecha_entrega']

    def get_view_description(self, html=False):
        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)

        if user and user.is_authenticated and (getattr(user, 'es_profesor', False) or getattr(user, 'es_administrador', False)):
            from apps.cursos.models import Curso
            if user.es_profesor and not user.es_administrador:
                cursos = Curso.objects.filter(profesor=user).order_by('nombre')
            else:
                cursos = Curso.objects.all().order_by('nombre')

            buttons_html = '<div style="margin: 12px 0; display: flex; flex-wrap: wrap; gap: 8px;">'
            buttons_html += '<a href="/api/v1/asignaciones/" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Ver Todas</a>'
            for c in cursos:
                buttons_html += f'<a href="/api/v1/asignaciones/?curso={c.id}" style="background: #2563eb; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Curso {c.codigo}: {c.nombre}</a>'
            buttons_html += '</div>'

            content = (
                '<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">'
                '<h3 style="margin-top: 0; color: #0f172a;">Gestion y Creacion de Asignaciones</h3>'
                '<p style="color: #475569; margin-bottom: 10px; font-size: 14px;">'
                '1. En el formulario inferior puedes crear una nueva tarea seleccionando el <strong>Curso</strong> en el menu desplegable.<br>'
                '2. En la lista inferior, haz clic en el enlace <code>url_entrega</code> de cualquier asignacion para ver y calificar a los estudiantes.'
                '</p>'
                '<h4 style="margin: 12px 0 6px 0; color: #1e293b;">Filtrar asignaciones por curso (Haz clic para filtrar):</h4>'
                f'{buttons_html}'
                '</div>'
            )
            return mark_safe(content) if html else "Gestion y Creacion de Asignaciones"

        elif user and user.is_authenticated and getattr(user, 'es_estudiante', False):
            from apps.cursos.models import Curso
            cursos = Curso.objects.filter(
                inscripciones__estudiante=user,
                inscripciones__estado=Inscripcion.Estado.ACTIVA,
            ).order_by('nombre')

            buttons_html = '<div style="margin: 12px 0; display: flex; flex-wrap: wrap; gap: 8px;">'
            buttons_html += '<a href="/api/v1/asignaciones/" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Ver Todas</a>'
            for c in cursos:
                buttons_html += f'<a href="/api/v1/asignaciones/?curso={c.id}" style="background: #2563eb; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Curso {c.codigo}: {c.nombre}</a>'
            buttons_html += '</div>'

            content = (
                '<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">'
                '<h3 style="margin-top: 0; color: #0f172a;">Mis Asignaciones Academicas</h3>'
                '<p style="color: #475569; margin-bottom: 10px; font-size: 14px;">'
                '1. Revisa las tareas pendientes de tus cursos en la lista inferior.<br>'
                '2. Haz clic en el enlace <code>url_entrega</code> de la tarea para enviar tu solucion.'
                '</p>'
                '<h4 style="margin: 12px 0 6px 0; color: #1e293b;">Filtrar por curso (Haz clic):</h4>'
                f'{buttons_html}'
                '</div>'
            )
            return mark_safe(content) if html else "Mis Asignaciones Academicas"

        return mark_safe("<p>Inicia sesion para visualizar tus cursos y asignaciones.</p>") if html else "Inicia sesion"

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), EsProfesor()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AsignacionCrearActualizarSerializer
        return AsignacionListaSerializer

    def _obtener_curso(self, obligatorio=False):
        """
        Obtiene el curso desde el query param ?curso={id} o request.data['curso'].
        Valida que el profesor tenga permiso sobre ese curso.
        """
        from apps.cursos.models import Curso
        from rest_framework.exceptions import PermissionDenied, NotFound, ParseError

        curso_id = self.request.query_params.get('curso')
        if not curso_id and hasattr(self.request, 'data') and isinstance(self.request.data, dict):
            curso_id = self.request.data.get('curso')

        if not curso_id:
            if obligatorio:
                raise ParseError(
                    'Debes indicar el ID del curso al que pertenece la asignación. '
                    'Usa: /api/v1/asignaciones/?curso=<id_del_curso>'
                )
            return None

        try:
            curso = Curso.objects.select_related('profesor').get(pk=curso_id)
        except Curso.DoesNotExist:
            raise NotFound('El curso especificado no existe.')
        except (ValueError, TypeError):
            raise ParseError('El parametro "curso" debe ser un numero entero valido.')

        # Para crear: el profesor propietario o un administrador pueden agregar asignaciones
        if self.request.method == 'POST':
            if not (getattr(self.request.user, 'es_administrador', False) or (getattr(self.request.user, 'es_profesor', False) and curso.profesor == self.request.user)):
                raise PermissionDenied(
                    'Solo el profesor propietario del curso o un administrador puede agregar asignaciones.'
                )

        # Para listar: el estudiante debe estar inscrito
        if self.request.method == 'GET' and getattr(self.request.user, 'es_estudiante', False):
            if not Inscripcion.objects.filter(
                curso=curso,
                estudiante=self.request.user,
                estado=Inscripcion.Estado.ACTIVA,
            ).exists():
                raise PermissionDenied(
                    'Debes estar inscrito en el curso para ver sus asignaciones.'
                )

        return curso

    def get_queryset(self):
        usuario = self.request.user
        if not usuario or not usuario.is_authenticated:
            return Asignacion.objects.none()

        curso = self._obtener_curso(obligatorio=False)
        if curso:
            return Asignacion.objects.filter(curso=curso).annotate(
                total_entregas_anotado=Count('entregas', distinct=True)
            ).order_by('fecha_entrega')

        # Si no se filtra por curso específico, listar asignaciones según rol
        if getattr(usuario, 'es_profesor', False):
            return Asignacion.objects.filter(curso__profesor=usuario).annotate(
                total_entregas_anotado=Count('entregas', distinct=True)
            ).order_by('fecha_entrega')
        elif getattr(usuario, 'es_estudiante', False):
            return Asignacion.objects.filter(
                curso__inscripciones__estudiante=usuario,
                curso__inscripciones__estado=Inscripcion.Estado.ACTIVA,
            ).annotate(
                total_entregas_anotado=Count('entregas', distinct=True)
            ).order_by('fecha_entrega')
        elif getattr(usuario, 'es_administrador', False):
            return Asignacion.objects.all().annotate(
                total_entregas_anotado=Count('entregas', distinct=True)
            ).order_by('fecha_entrega')

        return Asignacion.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            curso = self._obtener_curso(obligatorio=False)
            if curso:
                context['curso'] = curso
        return context

    def create(self, request, *args, **kwargs):
        context = self.get_serializer_context()
        curso = self._obtener_curso(obligatorio=False)
        if curso:
            context['curso'] = curso
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        asignacion = serializer.save()
        return Response(
            {
                'exito': True,
                'mensaje': f'Asignacion "{asignacion.titulo}" creada exitosamente.',
                'id': asignacion.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class AsignacionDetalleActualizarView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/asignaciones/{id}/  -> Detalle de la asignacion.
    PATCH  /api/v1/asignaciones/{id}/  -> Actualizar asignacion.
    DELETE /api/v1/asignaciones/{id}/  -> Eliminar asignacion.
    """

    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT', 'DELETE'):
            return [IsAuthenticated(), EsProfesor()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return AsignacionCrearActualizarSerializer
        return AsignacionDetalleSerializer

    def get_queryset(self):
        return Asignacion.objects.select_related('curso', 'curso__profesor')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method in ('PATCH', 'PUT'):
            context['curso'] = self.get_object().curso
        return context

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        # Verificar que el profesor sea el propietario del curso de la asignacion
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if not request.user.es_administrador and request.user.es_profesor and obj.curso.profesor != request.user:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    'Solo el profesor propietario del curso o un administrador puede modificar esta asignacion.'
                )

    def perform_destroy(self, instance):
        if instance.entregas.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'No se puede eliminar una asignacion que ya tiene entregas de estudiantes.'
            )
        instance.delete()

class EntregaListaCrearView(generics.ListCreateAPIView):
    """
    Gestion y envio de entregas para esta asignacion.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'estudiante']
    search_fields = ['estudiante__email', 'estudiante__username', 'estudiante__first_name', 'estudiante__last_name']
    ordering_fields = ['fecha_entrega', 'calificacion', 'estado']
    ordering = ['-fecha_entrega']

    def get_view_description(self, html=False):
        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)
        asignacion_actual = None
        try:
            asignacion_actual = self._obtener_asignacion()
        except Exception:
            pass

        if not asignacion_actual:
            return mark_safe("<p>Gestion y consulta de entregas.</p>") if html else "Gestion de entregas"

        # Banner de detalles de la asignación
        banner_html = f'''
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
            <h3 style="margin-top: 0; color: #0f172a;">Asignacion: {asignacion_actual.titulo}</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; color: #475569;">
                <div><strong>Curso:</strong> {asignacion_actual.curso.nombre} ({asignacion_actual.curso.codigo})</div>
                <div><strong>Tipo:</strong> {asignacion_actual.get_tipo_display()}</div>
                <div><strong>Porcentaje:</strong> {asignacion_actual.porcentaje}%</div>
                <div><strong>Puntaje Maximo:</strong> {asignacion_actual.valor_maximo} pts</div>
                <div><strong>Fecha limite:</strong> {asignacion_actual.fecha_entrega.strftime('%d/%m/%Y %H:%M')}</div>
            </div>
        </div>
        '''

        # Barra de botones para cambiar de asignación
        nav_asig_html = ""
        if user and user.is_authenticated:
            if getattr(user, 'es_profesor', False) or getattr(user, 'es_administrador', False):
                if getattr(user, 'es_profesor', False) and not getattr(user, 'es_administrador', False):
                    asignaciones_prof = Asignacion.objects.filter(
                        curso__profesor=user
                    ).select_related('curso').order_by('curso__nombre', 'fecha_entrega')
                else:
                    asignaciones_prof = Asignacion.objects.select_related('curso').order_by('curso__nombre', 'fecha_entrega')

                if asignaciones_prof.exists():
                    nav_asig_html = '<div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; margin-bottom: 16px;">'
                    nav_asig_html += '<h4 style="margin-top: 0; margin-bottom: 8px; color: #1e293b; font-size: 14px;">Cambiar de Asignacion (Haz clic):</h4>'
                    nav_asig_html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">'
                    for asig in asignaciones_prof:
                        if asig.id == asignacion_actual.id:
                            nav_asig_html += f'<span style="background: #0f172a; color: #ffffff; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">{asig.titulo} (Actual)</span>'
                        else:
                            nav_asig_html += f'<a href="/api/v1/asignaciones/{asig.id}/entregas/" style="background: #e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">{asig.titulo}</a>'
                    nav_asig_html += '</div></div>'

            elif getattr(user, 'es_estudiante', False):
                asignaciones_est = Asignacion.objects.filter(
                    curso__inscripciones__estudiante=user,
                    curso__inscripciones__estado=Inscripcion.Estado.ACTIVA,
                ).select_related('curso').order_by('curso__nombre', 'fecha_entrega')

                if asignaciones_est.exists():
                    nav_asig_html = '<div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; margin-bottom: 16px;">'
                    nav_asig_html += '<h4 style="margin-top: 0; margin-bottom: 8px; color: #1e293b; font-size: 14px;">Mis Otras Asignaciones:</h4>'
                    nav_asig_html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">'
                    for asig in asignaciones_est:
                        if asig.id == asignacion_actual.id:
                            nav_asig_html += f'<span style="background: #0f172a; color: #ffffff; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">{asig.titulo} (Actual)</span>'
                        else:
                            nav_asig_html += f'<a href="/api/v1/asignaciones/{asig.id}/entregas/" style="background: #e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">{asig.titulo}</a>'
                    nav_asig_html += '</div></div>'

        if user and user.is_authenticated and (getattr(user, 'es_profesor', False) or getattr(user, 'es_administrador', False)):
            # Obtener todos los estudiantes inscritos en el curso
            inscripciones = Inscripcion.objects.filter(
                curso=asignacion_actual.curso,
                estado=Inscripcion.Estado.ACTIVA
            ).select_related('estudiante').order_by('estudiante__last_name', 'estudiante__first_name')

            entregas_map = {
                e.estudiante_id: e
                for e in Entrega.objects.filter(asignacion=asignacion_actual).select_related('estudiante')
            }

            rows_html = ""
            total_inscritos = inscripciones.count()
            total_entregas = len(entregas_map)

            for insc in inscripciones:
                est = insc.estudiante
                entrega = entregas_map.get(est.id)
                nombre_completo = f"{est.first_name} {est.last_name}".strip() or est.username

                if entrega:
                    if entrega.estado == Entrega.Estado.CALIFICADA:
                        estado_badge = f'<span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 12px;">Calificada ({entrega.calificacion}/{asignacion_actual.valor_maximo} pts - {asignacion_actual.porcentaje}%)</span>'
                        boton_accion = f'<a href="/api/v1/asignaciones/{asignacion_actual.id}/entregas/{entrega.id}/calificar/" style="background: #2563eb; color: #ffffff; padding: 5px 12px; border-radius: 5px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">Modificar Nota</a>'
                    else:
                        estado_badge = '<span style="background: #fef08a; color: #854d0e; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 12px;">Entregada (Sin Calificar)</span>'
                        boton_accion = f'<a href="/api/v1/asignaciones/{asignacion_actual.id}/entregas/{entrega.id}/calificar/" style="background: #16a34a; color: #ffffff; padding: 5px 12px; border-radius: 5px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">Calificar</a>'
                else:
                    estado_badge = '<span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 12px;">No ha entregado</span>'
                    boton_accion = '<span style="color: #94a3b8; font-size: 12px;">Sin entrega</span>'

                rows_html += f'''
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 10px 14px; font-size: 13px; color: #0f172a; font-weight: 500;">
                        {nombre_completo}
                        <div style="color: #64748b; font-size: 11px; font-weight: normal;">{est.email}</div>
                    </td>
                    <td style="padding: 10px 14px; font-size: 13px;">{estado_badge}</td>
                    <td style="padding: 10px 14px; font-size: 13px;">{boton_accion}</td>
                </tr>
                '''

            tabla_estudiantes = f'''
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-top: 16px;">
                <div style="background: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #0f172a; font-size: 14px; font-weight: 600;">Estado de Entregas por Estudiante ({total_entregas}/{total_inscritos} entregaron)</h4>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="background: #f1f5f9; border-bottom: 2px solid #e2e8f0;">
                                <th style="padding: 10px 14px; font-size: 12px; color: #475569; font-weight: 600;">Estudiante</th>
                                <th style="padding: 10px 14px; font-size: 12px; color: #475569; font-weight: 600;">Estado</th>
                                <th style="padding: 10px 14px; font-size: 12px; color: #475569; font-weight: 600;">Accion</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html if rows_html else '<tr><td colspan="3" style="padding: 14px; text-align: center; color: #64748b;">No hay estudiantes inscritos en este curso.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
            '''

            full_html = f'''
            {banner_html}
            {nav_asig_html}
            {tabla_estudiantes}
            '''
            return mark_safe(full_html) if html else "Revision y Calificacion de Entregas"

        elif user and user.is_authenticated and getattr(user, 'es_estudiante', False):
            mi_entrega = Entrega.objects.filter(asignacion=asignacion_actual, estudiante=user).first()
            if mi_entrega:
                if mi_entrega.estado == Entrega.Estado.CALIFICADA:
                    info_mi_entrega = f'<div style="background: #dcfce7; border: 1px solid #86efac; padding: 12px; border-radius: 6px; color: #166534; margin-top: 10px;"><strong>Tu Entrega esta Calificada:</strong> {mi_entrega.calificacion}/{asignacion_actual.valor_maximo} pts ({asignacion_actual.porcentaje}% del curso).<br><strong>Retroalimentacion:</strong> {mi_entrega.retroalimentacion or "Sin comentarios adicionales."}</div>'
                else:
                    info_mi_entrega = '<div style="background: #fef08a; border: 1px solid #fde047; padding: 12px; border-radius: 6px; color: #854d0e; margin-top: 10px;"><strong>Tu Entrega fue Enviada:</strong> Pendiente de calificacion por el profesor.</div>'
            else:
                info_mi_entrega = '<div style="background: #fee2e2; border: 1px solid #fca5a5; padding: 12px; border-radius: 6px; color: #991b1b; margin-top: 10px;"><strong>Aun no has entregado esta asignacion.</strong> Completa el formulario inferior para enviar tu solucion.</div>'

            full_html = f'''
            {banner_html}
            {nav_asig_html}
            {info_mi_entrega}
            '''
            return mark_safe(full_html) if html else "Envio de Solucion"

        return mark_safe(f"{banner_html}<p>Inicia sesion para ver o enviar entregas segun tu rol.</p>") if html else "Gestion de entregas"

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), EsEstudiante()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EntregaCrearSerializer
        return EntregaListaSerializer

    def _obtener_asignacion(self):
        from rest_framework.exceptions import NotFound
        asignacion_id = self.kwargs['asignacion_id']
        try:
            return Asignacion.objects.select_related(
                'curso', 'curso__profesor'
            ).get(pk=asignacion_id)
        except Asignacion.DoesNotExist:
            raise NotFound('La asignacion especificada no existe.')

    def get_queryset(self):
        asignacion = self._obtener_asignacion()
        usuario = self.request.user

        # El profesor del curso o un administrador ve todas las entregas
        if usuario.es_administrador or (usuario.es_profesor and asignacion.curso.profesor == usuario):
            return Entrega.objects.filter(asignacion=asignacion).select_related(
                'estudiante', 'asignacion'
            )

        # El estudiante solo ve su propia entrega
        if usuario.es_estudiante:
            return Entrega.objects.filter(
                asignacion=asignacion,
                estudiante=usuario,
            ).select_related('estudiante', 'asignacion')

        return Entrega.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['asignacion'] = self._obtener_asignacion()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entrega = serializer.save()
        return Response(
            {
                'exito': True,
                'mensaje': 'Entrega registrada exitosamente.',
                'entrega_id': entrega.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class EntregaDetalleView(generics.RetrieveAPIView):
    """
    GET /api/v1/asignaciones/{asignacion_id}/entregas/{pk}/
    """
    serializer_class = EntregaDetalleSerializer
    permission_classes = [IsAuthenticated, EsPropietarioDeLaEntrega]

    def get_queryset(self):
        return Entrega.objects.select_related(
            'estudiante', 'asignacion', 'asignacion__curso', 'asignacion__curso__profesor'
        )


class CalificarEntregaView(generics.GenericAPIView):
    """
    Endpoint para que el profesor califique una entrega específica.
    """
    serializer_class = CalificarEntregaSerializer
    permission_classes = [IsAuthenticated, EsProfesor]

    def get_view_description(self, html=False):
        asignacion_id = self.kwargs.get('asignacion_id')
        back_url = f"/api/v1/asignaciones/{asignacion_id}/entregas/" if asignacion_id else "/api/v1/asignaciones/"

        content = (
            '<div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-bottom: 16px;">'
            '<h3 style="margin-top: 0; color: #0f172a;">Calificacion y Retroalimentacion de la Entrega</h3>'
            '<p style="color: #475569; font-size: 14px; margin-bottom: 12px;">'
            '1. En el formulario inferior ingresa la nota numerica y tus comentarios.<br>'
            '2. Haz clic en el boton <strong>PATCH</strong> para guardar la calificacion.'
            '</p>'
            f'<a href="{back_url}" style="background: #0f172a; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">&larr; Volver a la Lista de Entregas</a>'
            '</div>'
        )
        return mark_safe(content) if html else "Calificacion y retroalimentacion de la entrega"

    def _obtener_entrega(self):
        from rest_framework.exceptions import NotFound, PermissionDenied
        try:
            entrega = Entrega.objects.select_related(
                'asignacion', 'asignacion__curso', 'asignacion__curso__profesor',
                'estudiante',
            ).get(
                pk=self.kwargs['pk'],
                asignacion_id=self.kwargs['asignacion_id'],
            )
        except Entrega.DoesNotExist:
            raise NotFound('La entrega especificada no existe.')

        if not (self.request.user.es_administrador or entrega.asignacion.curso.profesor == self.request.user):
            raise PermissionDenied(
                'Solo el profesor del curso o un administrador puede calificar esta entrega.'
            )

        return entrega

    def get(self, request, *args, **kwargs):
        """Muestra los detalles de la entrega a calificar y habilita el formulario interactivo."""
        entrega = self._obtener_entrega()
        serializer = EntregaDetalleSerializer(entrega)
        return Response({
            'mensaje': 'Detalles de la entrega enviada por el estudiante:',
            'entrega': serializer.data,
        })

    def patch(self, request, *args, **kwargs):
        return self._procesar_calificacion(request)

    def post(self, request, *args, **kwargs):
        return self._procesar_calificacion(request)

    def _procesar_calificacion(self, request):
        entrega = self._obtener_entrega()

        raw_data = request.data
        if isinstance(raw_data, (int, float, str)):
            datos = {'calificacion': raw_data, 'retroalimentacion': ''}
        elif isinstance(raw_data, dict):
            datos = raw_data
        else:
            datos = {}

        if datos.get('accion') == 'devolver':
            entrega.devolver(retroalimentacion=datos.get('retroalimentacion', 'Debes volver a realizar esta tarea.'))
            return Response({
                'exito': True,
                'mensaje': 'Entrega devuelta al estudiante para revision.',
                'estado': entrega.estado,
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(
            data=datos,
            context={'entrega': entrega, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        entrega_calificada = serializer.save()

        return Response(
            {
                'exito': True,
                'mensaje': 'Calificacion guardada exitosamente.',
                'calificacion': str(entrega_calificada.calificacion),
                'porcentaje': str(entrega_calificada.asignacion.porcentaje),
                'valor_maximo': str(entrega_calificada.asignacion.valor_maximo),
                'retroalimentacion': entrega_calificada.retroalimentacion,
            },
            status=status.HTTP_200_OK,
        )


class CalificarEstudianteAsignacionView(generics.GenericAPIView):
    """
    POST /api/v1/asignaciones/{asignacion_id}/estudiantes/{estudiante_id}/calificar/
    Permite al profesor calificar o modificar directamente la nota de un estudiante para una tarea especifica.
    """
    permission_classes = [IsAuthenticated, EsProfesor]

    def post(self, request, asignacion_id, estudiante_id):
        from apps.usuarios.models import Usuario

        try:
            asignacion = Asignacion.objects.select_related('curso').get(pk=asignacion_id)
        except Asignacion.DoesNotExist:
            return Response({'error': 'Asignacion no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if not (request.user.es_administrador or asignacion.curso.profesor == request.user):
            return Response({'error': 'No tienes permisos para calificar en este curso.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            estudiante = Usuario.objects.get(pk=estudiante_id, rol='estudiante')
        except Usuario.DoesNotExist:
            return Response({'error': 'Estudiante no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        entrega, _ = Entrega.objects.get_or_create(
            asignacion=asignacion,
            estudiante=estudiante,
            defaults={
                'contenido': 'Calificacion / Registro directo por el profesor.',
                'estado': Entrega.Estado.ENVIADA,
            }
        )

        accion = request.data.get('accion')
        if accion == 'devolver':
            retro = request.data.get('retroalimentacion', 'Debes volver a realizar esta tarea.')
            entrega.devolver(retroalimentacion=retro)
            return Response({
                'exito': True,
                'mensaje': f'Asignacion "{asignacion.titulo}" marcada para que el estudiante la vuelva a hacer.',
                'estado': entrega.estado,
            }, status=status.HTTP_200_OK)

        nota = request.data.get('calificacion')
        if nota is None or str(nota).strip() == '':
            return Response({'error': 'Debes ingresar una calificacion numerica.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nota_float = float(nota)
        except (ValueError, TypeError):
            return Response({'error': 'La calificacion debe ser un numero valido.'}, status=status.HTTP_400_BAD_REQUEST)

        if nota_float < 0 or nota_float > float(asignacion.valor_maximo):
            return Response({'error': f'La nota debe estar entre 0 y {asignacion.valor_maximo}.'}, status=status.HTTP_400_BAD_REQUEST)

        retro = request.data.get('retroalimentacion', '')
        entrega.calificar(nota=nota_float, retroalimentacion=retro)

        return Response({
            'exito': True,
            'mensaje': f'Nota guardada para "{asignacion.titulo}": {nota_float}/{asignacion.valor_maximo}.',
            'calificacion': nota_float,
            'estado': entrega.estado,
        }, status=status.HTTP_200_OK)

    def get(self, request, asignacion_id, estudiante_id):
        return Response({'mensaje': 'Utiliza el metodo POST para calificar o modificar la nota.'})
