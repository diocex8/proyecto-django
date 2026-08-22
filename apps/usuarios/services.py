"""
apps/usuarios/services.py

Capa de servicio del dominio de usuarios.
"""

import logging

from django.db.models import Count, Avg, Q

from .models import Usuario

logger = logging.getLogger('gestion_academica')


def obtener_estadisticas_estudiante(estudiante):
    """
    Calcula el resumen academico completo de un estudiante.

    Usa una sola consulta con anotaciones para obtener todos los datos
    en lugar de multiples consultas individuales (evita N+1).

    Retorna: dict con estadisticas del estudiante.
    """
    from apps.inscripciones.models import Inscripcion
    from apps.asignaciones.models import Entrega

    inscripciones = Inscripcion.objects.filter(
        estudiante=estudiante
    ).select_related('curso').order_by('-fecha_inscripcion')

    total_activas = inscripciones.filter(estado=Inscripcion.Estado.ACTIVA).count()
    total_completadas = inscripciones.filter(estado=Inscripcion.Estado.COMPLETADA).count()

    # Promedio global de todas las entregas calificadas
    promedio_global = Entrega.objects.filter(
        estudiante=estudiante,
        estado=Entrega.Estado.CALIFICADA,
    ).aggregate(promedio=Avg('calificacion'))['promedio']

    return {
        'total_inscripciones_activas': total_activas,
        'total_cursos_completados': total_completadas,
        'promedio_global': round(float(promedio_global), 2) if promedio_global else None,
    }


def obtener_estadisticas_profesor(profesor):
    """
    Calcula el resumen de actividad de un profesor.
    Usa anotaciones para obtener todos los datos en una sola consulta.
    """
    from apps.cursos.models import Curso

    resumen = Curso.objects.filter(profesor=profesor).aggregate(
        total_cursos=Count('id'),
        total_publicados=Count('id', filter=Q(estado=Curso.Estado.PUBLICADO)),
        total_archivados=Count('id', filter=Q(estado=Curso.Estado.ARCHIVADO)),
    )

    return {
        'total_cursos': resumen['total_cursos'] or 0,
        'cursos_publicados': resumen['total_publicados'] or 0,
        'cursos_archivados': resumen['total_archivados'] or 0,
    }
