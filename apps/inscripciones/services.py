"""
apps/inscripciones/services.py

Capa de servicio del dominio de inscripciones.

Decision de arquitectura:
    La logica de inscripcion tiene reglas de negocio no triviales:
    verificar cupos, calcular nota final promedio, etc. Centralizar esto
    en servicios permite que las vistas sean delgadas y que esta logica
    sea testeable sin necesidad de peticiones HTTP.
"""

import logging

from django.db.models import Avg, Count, Q

logger = logging.getLogger('gestion_academica')


def calcular_nota_final_inscripcion(inscripcion):
    """
    Calcula y actualiza la nota final de una inscripcion a partir de
    todas las entregas calificadas del estudiante en el curso.

    La nota final es el promedio ponderado de todas las calificaciones
    dividido por los valores maximos de cada asignacion.

    Args:
        inscripcion: instancia del modelo Inscripcion.

    Returns:
        Decimal con la nota final calculada, o None si no hay entregas calificadas.
    """
    from apps.asignaciones.models import Entrega, Asignacion
    from decimal import Decimal

    asignaciones = Asignacion.objects.filter(curso=inscripcion.curso)
    if not asignaciones.exists():
        return None

    entregas_calificadas = Entrega.objects.filter(
        asignacion__in=asignaciones,
        estudiante=inscripcion.estudiante,
        estado=Entrega.Estado.CALIFICADA,
    ).select_related('asignacion')

    if not entregas_calificadas.exists():
        return None

    suma_ponderada = Decimal('0')
    suma_maximos = Decimal('0')

    for entrega in entregas_calificadas:
        suma_ponderada += entrega.calificacion
        suma_maximos += entrega.asignacion.valor_maximo

    if suma_maximos == 0:
        return None

    nota_final = (suma_ponderada / suma_maximos) * 100
    return nota_final.quantize(Decimal('0.01'))


def inscribir_estudiante(curso, estudiante):
    """
    Servicio transaccional para inscribir un estudiante en un curso.

    Centraliza todas las validaciones de negocio previas a la inscripcion:
    - El curso debe estar publicado.
    - El estudiante no debe estar ya inscrito activamente.
    - El cupo del curso no debe estar agotado.

    Args:
        curso: instancia del modelo Curso.
        estudiante: instancia del modelo Usuario (rol ESTUDIANTE).

    Returns:
        Inscripcion recien creada.

    Raises:
        ValueError: si alguna regla de negocio no se cumple.
    """
    from .models import Inscripcion
    from apps.cursos.models import Curso

    if curso.estado != Curso.Estado.PUBLICADO:
        raise ValueError(
            'Solo puedes inscribirte en cursos que esten publicados.'
        )

    ya_inscrito = Inscripcion.objects.filter(
        curso=curso,
        estudiante=estudiante,
        estado=Inscripcion.Estado.ACTIVA,
    ).exists()

    if ya_inscrito:
        raise ValueError(
            'Ya estas inscrito activamente en este curso.'
        )

    # Verificar cupo si el curso lo define
    if curso.cupo_maximo is not None:
        total_activos = Inscripcion.objects.filter(
            curso=curso,
            estado=Inscripcion.Estado.ACTIVA,
        ).count()
        if total_activos >= curso.cupo_maximo:
            raise ValueError(
                f'El curso ha alcanzado su cupo maximo de {curso.cupo_maximo} estudiantes.'
            )

    inscripcion = Inscripcion.objects.create(
        curso=curso,
        estudiante=estudiante,
        estado=Inscripcion.Estado.ACTIVA,
    )
    logger.info(
        'Inscripcion creada via servicio. Estudiante: %s, Curso: %s',
        estudiante.email, curso.codigo,
    )
    return inscripcion
