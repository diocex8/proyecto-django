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
from rest_framework import generics, status
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


# ===========================================================================
# Vistas de ASIGNACION
# ===========================================================================

class AsignacionListaCrearView(generics.ListCreateAPIView):
    """
    Listado y gestion de asignaciones del curso.
    """

    def get_view_description(self, html=False):
        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)

        if user and user.is_authenticated and getattr(user, 'es_profesor', False):
            from apps.cursos.models import Curso
            cursos = Curso.objects.filter(profesor=user).order_by('nombre')
            cursos_nav = "\n\n**Filtrar asignaciones por curso:**\n- [Ver todas mis asignaciones](/api/v1/asignaciones/)\n"
            for c in cursos:
                cursos_nav += f"- [Curso {c.codigo}: {c.nombre}](/api/v1/asignaciones/?curso={c.id})\n"

            return (
                "### Gestion y Creacion de Asignaciones\n\n"
                "**Instrucciones:**\n"
                "1. En el formulario inferior puedes crear una nueva tarea seleccionando el **Curso** en el menu desplegable.\n"
                "2. En la lista de resultados inferior, cada asignacion cuenta con el enlace `url_entrega` para ver y calificar las entregas de los estudiantes."
                f"{cursos_nav}"
            )
        elif user and user.is_authenticated and getattr(user, 'es_estudiante', False):
            from apps.cursos.models import Curso
            cursos = Curso.objects.filter(
                inscripciones__estudiante=user,
                inscripciones__estado=Inscripcion.Estado.ACTIVA,
            ).order_by('nombre')
            cursos_nav = "\n\n**Filtrar asignaciones por curso:**\n- [Ver todas mis asignaciones](/api/v1/asignaciones/)\n"
            for c in cursos:
                cursos_nav += f"- [Curso {c.codigo}: {c.nombre}](/api/v1/asignaciones/?curso={c.id})\n"

            return (
                "### Mis Asignaciones Academicas\n\n"
                "**Instrucciones:**\n"
                "1. Revisa las tareas pendientes de tus cursos en la lista inferior.\n"
                "2. Haz clic en el enlace `url_entrega` de la asignacion deseada para enviar tu solucion."
                f"{cursos_nav}"
            )

        return (
            "Listado de asignaciones del curso.\n\n"
            "Inicia sesion para visualizar tus cursos y asignaciones."
        )

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

        # Para crear: solo el profesor propietario puede agregar asignaciones
        if self.request.method == 'POST':
            if not getattr(self.request.user, 'es_profesor', False) or curso.profesor != self.request.user:
                raise PermissionDenied(
                    'Solo el profesor propietario del curso puede agregar asignaciones.'
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
            if request.user.es_profesor and obj.curso.profesor != request.user:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    'Solo el profesor propietario del curso puede modificar esta asignacion.'
                )

    def perform_destroy(self, instance):
        if instance.entregas.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'No se puede eliminar una asignacion que ya tiene entregas de estudiantes.'
            )
        instance.delete()


# ===========================================================================
# Vistas de ENTREGA
# ===========================================================================

class EntregaListaCrearView(generics.ListCreateAPIView):
    """
    Gestion y envio de entregas para esta asignacion.
    """

    def get_view_description(self, html=False):
        user = getattr(self, 'request', None) and getattr(self.request, 'user', None)
        asignacion_actual = None
        try:
            asignacion_actual = self._obtener_asignacion()
        except Exception:
            pass

        info_asignacion = ""
        if asignacion_actual:
            info_asignacion = (
                f"### Asignacion: {asignacion_actual.titulo}\n"
                f"- **Curso:** {asignacion_actual.curso.nombre} ({asignacion_actual.curso.codigo})\n"
                f"- **Tipo:** {asignacion_actual.get_tipo_display()} | **Valor Maximo:** {asignacion_actual.valor_maximo} pts\n"
                f"- **Fecha limite:** {asignacion_actual.fecha_entrega.strftime('%d/%m/%Y %H:%M')}\n\n"
            )

        otras_asignaciones_nav = ""
        if user and user.is_authenticated:
            if getattr(user, 'es_profesor', False):
                asignaciones_prof = Asignacion.objects.filter(
                    curso__profesor=user
                ).select_related('curso').order_by('curso__nombre', 'fecha_entrega')

                if asignaciones_prof.exists():
                    otras_asignaciones_nav = "\n\n---\n### Cambiar de Asignacion (Clic para ver entregas):\n"
                    curso_actual_nombre = None
                    for asig in asignaciones_prof:
                        if asig.curso.nombre != curso_actual_nombre:
                            curso_actual_nombre = asig.curso.nombre
                            otras_asignaciones_nav += f"\n**Curso: {curso_actual_nombre}**\n"
                        icono = "*(Viendo actualmente)*" if asignacion_actual and asig.id == asignacion_actual.id else ""
                        otras_asignaciones_nav += f"- [{asig.titulo}](/api/v1/asignaciones/{asig.id}/entregas/) {icono}\n"

            elif getattr(user, 'es_estudiante', False):
                asignaciones_est = Asignacion.objects.filter(
                    curso__inscripciones__estudiante=user,
                    curso__inscripciones__estado=Inscripcion.Estado.ACTIVA,
                ).select_related('curso').order_by('curso__nombre', 'fecha_entrega')

                if asignaciones_est.exists():
                    otras_asignaciones_nav = "\n\n---\n### Mis Asignaciones (Clic para enviar o ver entrega):\n"
                    curso_actual_nombre = None
                    for asig in asignaciones_est:
                        if asig.curso.nombre != curso_actual_nombre:
                            curso_actual_nombre = asig.curso.nombre
                            otras_asignaciones_nav += f"\n**Curso: {curso_actual_nombre}**\n"
                        icono = "*(Viendo actualmente)*" if asignacion_actual and asig.id == asignacion_actual.id else ""
                        otras_asignaciones_nav += f"- [{asig.titulo}](/api/v1/asignaciones/{asig.id}/entregas/) {icono}\n"

        if user and user.is_authenticated and getattr(user, 'es_estudiante', False):
            return (
                f"{info_asignacion}"
                "### Envio de Solucion\n\n"
                "**Instrucciones:**\n"
                "1. En el formulario inferior puedes redactar tu entrega (en formato JSON: `{\"contenido\": \"Tu texto...\"}`).\n"
                "2. Recuerda que solo se permite una entrega por asignacion antes de la fecha limite.\n"
                f"{otras_asignaciones_nav}"
            )
        elif user and user.is_authenticated and getattr(user, 'es_profesor', False):
            return (
                f"{info_asignacion}"
                "### Revision y Calificacion de Entregas\n\n"
                "**Instrucciones:**\n"
                "1. En la lista inferior (en `resultados`) veras las entregas de tus estudiantes.\n"
                "2. Para calificar a un estudiante, haz clic en el enlace `url_calificar` de su entrega.\n"
                f"{otras_asignaciones_nav}"
            )

        return (
            "Gestion y consulta de entregas de la asignacion.\n\n"
            "Inicia sesion para ver o enviar entregas segun tu rol."
        )

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

        # El profesor del curso ve todas las entregas
        if usuario.es_profesor and asignacion.curso.profesor == usuario:
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
        return (
            "Calificación y retroalimentación de la entrega del estudiante.\n\n"
            "INSTRUCCIONES:\n"
            "1. En el formulario inferior (pestaña 'HTML form') encontrarás las casillas 'Calificacion' y 'Retroalimentacion'.\n"
            "2. Solo escribe la nota numérica (ejemplo: 20 o 18.5) y tus comentarios.\n"
            "3. Haz clic en el botón PATCH para guardar la calificación."
        )

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

        if entrega.asignacion.curso.profesor != self.request.user:
            raise PermissionDenied(
                'Solo el profesor del curso puede calificar esta entrega.'
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

        if entrega.estado == Entrega.Estado.CALIFICADA:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Esta entrega ya ha sido calificada.')

        raw_data = request.data
        if isinstance(raw_data, (int, float, str)):
            datos = {'calificacion': raw_data, 'retroalimentacion': ''}
        elif isinstance(raw_data, dict):
            datos = raw_data
        else:
            datos = {}

        serializer = self.get_serializer(
            data=datos,
            context={'entrega': entrega, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        entrega_calificada = serializer.save()

        return Response(
            {
                'exito': True,
                'mensaje': 'Entrega calificada exitosamente.',
                'calificacion': str(entrega_calificada.calificacion),
                'valor_maximo': str(entrega_calificada.asignacion.valor_maximo),
                'retroalimentacion': entrega_calificada.retroalimentacion,
            },
            status=status.HTTP_200_OK,
        )
