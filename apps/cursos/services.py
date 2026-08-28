"""
Capa de servicio del dominio de cursos.
Logica de negocio reutilizable que no pertenece ni al modelo ni a la vista.
"""

import logging

from django.db.models import Count, Avg, Q

logger = logging.getLogger('gestion_academica')


def obtener_reporte_curso(curso_id):
    """
    Genera un reporte completo de un curso: inscripciones, entregas y promedios.
    Usa una sola consulta anotada para evitar N+1.
    """
    from .models import Curso
    from apps.inscripciones.models import Inscripcion
    from apps.asignaciones.models import Entrega

    try:
        curso = Curso.objects.select_related('profesor').get(pk=curso_id)
    except Curso.DoesNotExist:
        return None

    stats_inscripciones = Inscripcion.objects.filter(curso=curso).aggregate(
        total_activas=Count('id', filter=Q(estado=Inscripcion.Estado.ACTIVA)),
        total_retiradas=Count('id', filter=Q(estado=Inscripcion.Estado.RETIRADA)),
        total_completadas=Count('id', filter=Q(estado=Inscripcion.Estado.COMPLETADA)),
    )

    stats_entregas = Entrega.objects.filter(
        asignacion__curso=curso,
        estado=Entrega.Estado.CALIFICADA,
    ).aggregate(
        total_calificadas=Count('id'),
        promedio_general=Avg('calificacion'),
    )

    return {
        'curso': str(curso),
        'profesor': curso.profesor.get_full_name(),
        'inscripciones': stats_inscripciones,
        'entregas': {
            'total_calificadas': stats_entregas['total_calificadas'] or 0,
            'promedio_general': (
                round(float(stats_entregas['promedio_general']), 2)
                if stats_entregas['promedio_general'] else None
            ),
        },
    }
