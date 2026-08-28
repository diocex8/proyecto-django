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

        if not (user and user.is_authenticated and (user.es_profesor or user.es_administrador)):
            return "Inscripciones" if not html else ""

        from apps.cursos.models import Curso
        from apps.asignaciones.models import Entrega

        if user.es_profesor and not user.es_administrador:
            cursos = Curso.objects.filter(profesor=user).order_by('nombre')
            inscripciones_qs = Inscripcion.objects.filter(
                curso__profesor=user
            ).select_related('curso', 'estudiante').prefetch_related(
                'curso__asignaciones',
                'estudiante__entregas_como_estudiante__asignacion'
            ).order_by('-fecha_inscripcion')
        else:
            cursos = Curso.objects.all().order_by('nombre')
            inscripciones_qs = Inscripcion.objects.all().select_related(
                'curso', 'estudiante'
            ).prefetch_related(
                'curso__asignaciones',
                'estudiante__entregas_como_estudiante__asignacion'
            ).order_by('-fecha_inscripcion')

        curso_filtro = getattr(self, 'request', None) and self.request.GET.get('curso')
        if curso_filtro:
            inscripciones_qs = inscripciones_qs.filter(curso_id=curso_filtro)

        buttons_html = '<div style="margin: 8px 0 12px 0; display: flex; flex-wrap: wrap; gap: 8px;">'
        all_active_style = "background: #0f172a; color: #ffffff;" if not curso_filtro else "background: #e2e8f0; color: #334155;"
        buttons_html += f'<a href="/api/v1/inscripciones/" style="{all_active_style} padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Todas las Inscripciones</a>'
        for c in cursos:
            c_active_style = "background: #2563eb; color: #ffffff;" if str(c.id) == str(curso_filtro) else "background: #e2e8f0; color: #334155;"
            buttons_html += f'<a href="/api/v1/inscripciones/?curso={c.id}" style="{c_active_style} padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Curso {c.codigo}: {c.nombre}</a>'
        buttons_html += '</div>'

        nombres_estudiantes = set()
        for insc in inscripciones_qs:
            est = insc.estudiante
            nom = est.get_full_name() or est.username
            nombres_estudiantes.add(nom)
            if est.email:
                nombres_estudiantes.add(est.email)

        datalist_options = "".join([f'<option value="{n}">' for n in sorted(nombres_estudiantes)])

        search_html = f"""
        <div style="margin: 12px 0 16px 0; background: #f8fafc; padding: 14px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <div style="display: flex; gap: 8px; align-items: center;">
                <input type="text" id="buscador-estudiantes" list="sugerencias-estudiantes" placeholder="Escribe para buscar estudiante por nombre, correo, usuario o curso..." oninput="filtrarEstudiantesEnTiempoReal(this.value)" style="flex: 1; padding: 9px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                <datalist id="sugerencias-estudiantes">
                    {datalist_options}
                </datalist>
                <button type="button" onclick="document.getElementById('buscador-estudiantes').value=''; filtrarEstudiantesEnTiempoReal('');" style="background: #64748b; color: white; border: none; padding: 9px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px;">Limpiar</button>
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 6px;">Filtro en tiempo real: a medida que escribes letras se filtran los estudiantes inscritos y sus notas.</div>
        </div>
        """

        cards_html = '<div id="contenedor-cards-estudiantes" style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;">'

        total_inscripciones = len(inscripciones_qs)
        if total_inscripciones == 0:
            cards_html += """
            <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:16px; border-radius:8px; text-align:center; color:#64748b; font-size:13px;">
                No hay inscripciones registradas en este curso o filtro.
            </div>
            """

        for insc in inscripciones_qs[:60]:
            est = insc.estudiante
            est_nom = est.get_full_name() or est.username
            stats = insc.calcular_estadisticas_academicas()
            rendimiento = stats['estado_rendimiento']
            badge_color = "#16a34a" if "Aprobando" in rendimiento and "riesgo" not in rendimiento else ("#d97706" if "riesgo" in rendimiento else "#dc2626")
            estado_badge_color = "#d97706" if insc.estado == Inscripcion.Estado.PENDIENTE else ("#16a34a" if insc.estado == Inscripcion.Estado.ACTIVA else "#dc2626")

            asignaciones_curso = list(insc.curso.asignaciones.all())
            entregas_est = [e for e in est.entregas_como_estudiante.all() if e.asignacion.curso_id == insc.curso_id]
            entregadas_ids = set(e.asignacion_id for e in entregas_est)

            pendientes = [a.titulo for a in asignaciones_curso if a.id not in entregadas_ids]

            calificadas_list = []
            for e in entregas_est:
                if e.estado == Entrega.Estado.CALIFICADA and e.calificacion is not None:
                    calificadas_list.append(f"{e.asignacion.titulo}: <strong>{e.calificacion}/{e.asignacion.valor_maximo}</strong>")

            calificaciones_html = ", ".join(calificadas_list) if calificadas_list else "<span style='color:#94a3b8;'>Sin calificaciones aun</span>"

            if pendientes:
                pendientes_html = "".join([f"<span style='background:#fee2e2; color:#b91c1c; padding:2px 6px; border-radius:4px; font-size:11px; margin-right:4px; display:inline-block;'>{p}</span>" for p in pendientes])
            else:
                pendientes_html = "<span style='color:#16a34a; font-weight:600;'>Al dia (todas las tareas entregadas)</span>"

            search_data = f"{est_nom} {est.email} {est.username} {insc.curso.nombre} {insc.curso.codigo} {insc.estado} {rendimiento}".lower()

            acciones_btn = f'<a href="/api/v1/inscripciones/{insc.id}/" style="background:#2563eb; color:white; padding:5px 12px; border-radius:5px; text-decoration:none; font-size:12px; font-weight:600;">Ver Ficha y Calificar</a>'
            if insc.estado == Inscripcion.Estado.PENDIENTE:
                acciones_btn += f' <a href="/api/v1/inscripciones/{insc.id}/aprobar/" style="background:#16a34a; color:white; padding:5px 12px; border-radius:5px; text-decoration:none; font-size:12px; font-weight:600; margin-left:6px;">Aceptar</a>'
                acciones_btn += f' <a href="/api/v1/inscripciones/{insc.id}/rechazar/" style="background:#dc2626; color:white; padding:5px 12px; border-radius:5px; text-decoration:none; font-size:12px; font-weight:600; margin-left:6px;">Rechazar</a>'

            cards_html += f"""
            <div class="card-estudiante-inscrito" data-search="{search_data}" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                    <div>
                        <span style="font-size:15px; font-weight:700; color:#0f172a;">{est_nom}</span>
                        <span style="font-size:13px; color:#64748b; margin-left:6px;">({est.email})</span>
                        <div style="font-size:12px; color:#3b82f6; font-weight:600; margin-top:2px;">Curso: [{insc.curso.codigo}] {insc.curso.nombre}</div>
                    </div>
                    <div>
                        <span style="background:{estado_badge_color}; color:#ffffff; padding:3px 8px; border-radius:5px; font-size:11px; font-weight:700; text-transform:uppercase; margin-right:4px;">{insc.get_estado_display()}</span>
                        <span style="background:{badge_color}; color:#ffffff; padding:3px 8px; border-radius:5px; font-size:11px; font-weight:700;">{rendimiento}</span>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; background:#f8fafc; padding:10px; border-radius:6px; font-size:12px; color:#334155; margin-bottom:10px; border:1px solid #f1f5f9;">
                    <div><strong>Progreso Entregas:</strong> {stats['entregas_enviadas']}/{stats['total_asignaciones_planificadas']} ({stats['porcentaje_avance']}%)</div>
                    <div><strong>Promedio Actual:</strong> <span style="color:#2563eb; font-weight:700;">{stats['promedio_acumulado_base20'] or 'Sin calificar'}</span> / 20</div>
                    <div><strong>Nota Proyectada:</strong> <span style="color:#0f172a; font-weight:700;">{stats['nota_proyectada_curso']}</span> / 20</div>
                    <div><strong>Nota Final:</strong> <span style="color:#16a34a; font-weight:700;">{insc.nota_final or 'Pendiente'}</span></div>
                </div>

                <div style="font-size:12px; margin-bottom:6px;">
                    <strong>Notas registradas:</strong> {calificaciones_html}
                </div>

                <div style="font-size:12px; margin-bottom:12px;">
                    <strong>Tareas sin entregar / pendientes:</strong> {pendientes_html}
                </div>

                <div style="display:flex; justify-content:flex-end; gap:6px;">
                    {acciones_btn}
                </div>
            </div>
            """

        cards_html += """
            <div id="sin-resultados-estudiantes" style="display:none; background:#f1f5f9; padding:16px; border-radius:8px; text-align:center; color:#64748b; font-size:13px;">
                No se encontraron estudiantes que coincidan con la busqueda.
            </div>
        </div>
        """

        script_js = """
        <script>
        function filtrarEstudiantesEnTiempoReal(texto) {
            var term = (texto || '').toLowerCase().trim();
            var cards = document.querySelectorAll('.card-estudiante-inscrito');
            var visibles = 0;
            cards.forEach(function(card) {
                var search = card.getAttribute('data-search') || '';
                if (search.indexOf(term) !== -1) {
                    card.style.display = 'block';
                    visibles++;
                } else {
                    card.style.display = 'none';
                }
            });
            var noRes = document.getElementById('sin-resultados-estudiantes');
            if (noRes) {
                noRes.style.display = (visibles === 0 && cards.length > 0) ? 'block' : 'none';
            }
        }
        </script>
        """

        return mark_safe(buttons_html + search_html + cards_html + script_js) if html else "Inscripciones"

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
