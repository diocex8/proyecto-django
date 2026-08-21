"""
apps/asignaciones/services.py

Capa de servicio del dominio de asignaciones y entregas.

Decision de arquitectura:
    Las operaciones que involucran multiples modelos (Asignacion, Entrega,
    Inscripcion) se encapsulan aqui para mantener las vistas delgadas y
    la logica de negocio testeable de forma aislada.
"""

import logging

from django.db.models import Avg, Count, Q

logger = logging.getLogger('gestion_academica')


def obtener_resumen_asignacion(asignacion):
    """
    Genera estadisticas completas de una asignacion.

    Usa aggregates para hacer solo una consulta SQL en lugar de
    iterar sobre las entregas individualmente (evita N+1).

    Args:
        asignacion: instancia del modelo Asignacion.

    Returns:
        dict con estadisticas de la asignacion.
    """
    from .models import Entrega

    stats = Entrega.objects.filter(asignacion=asignacion).aggregate(
        total_entregas=Count('id'),
        total_calificadas=Count('id', filter=Q(estado=Entrega.Estado.CALIFICADA)),
        total_enviadas=Count('id', filter=Q(estado=Entrega.Estado.ENVIADA)),
        total_devueltas=Count('id', filter=Q(estado=Entrega.Estado.DEVUELTA)),
        promedio_calificacion=Avg(
            'calificacion',
            filter=Q(estado=Entrega.Estado.CALIFICADA),
        ),
    )

    promedio = stats['promedio_calificacion']
    return {
        'total_entregas': stats['total_entregas'] or 0,
        'total_calificadas': stats['total_calificadas'] or 0,
        'total_pendientes_de_calificar': stats['total_enviadas'] or 0,
        'total_devueltas': stats['total_devueltas'] or 0,
        'promedio_calificacion': round(float(promedio), 2) if promedio else None,
        'valor_maximo': float(asignacion.valor_maximo),
        'acepta_entregas': asignacion.acepta_entregas,
        'esta_vencida': asignacion.esta_vencida,
    }


def devolver_entrega_para_revision(entrega, retroalimentacion, profesor):
    """
    Cambia el estado de una entrega a DEVUELTA para que el estudiante
    la corrija, en lugar de calificarla directamente.

    Reglas de negocio:
    - Solo el profesor del curso puede devolver una entrega.
    - Solo se pueden devolver entregas en estado ENVIADA o CALIFICADA.
    - Al devolver, se elimina la calificacion previa si existia.

    Args:
        entrega: instancia del modelo Entrega.
        retroalimentacion: str con los comentarios del profesor.
        profesor: instancia del modelo Usuario (rol PROFESOR).

    Raises:
        PermissionError: si el usuario no es el profesor del curso.
        ValueError: si el estado de la entrega no permite la devolucion.
    """
    from .models import Entrega

    if entrega.asignacion.curso.profesor != profesor:
        raise PermissionError(
            'Solo el profesor del curso puede devolver entregas.'
        )

    estados_validos = [Entrega.Estado.ENVIADA, Entrega.Estado.CALIFICADA]
    if entrega.estado not in estados_validos:
        raise ValueError(
            f'No se puede devolver una entrega en estado "{entrega.get_estado_display()}".'
        )

    entrega.estado = Entrega.Estado.DEVUELTA
    entrega.retroalimentacion = retroalimentacion
    entrega.calificacion = None
    entrega.fecha_calificacion = None
    entrega.save(update_fields=[
        'estado', 'retroalimentacion', 'calificacion', 'fecha_calificacion'
    ])

    logger.info(
        'Entrega devuelta para revision. ID: %s, Profesor: %s',
        entrega.pk, profesor.email,
    )
    return entrega
