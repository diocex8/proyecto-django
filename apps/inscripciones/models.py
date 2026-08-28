"""
apps/inscripciones/models.py

Modelo de inscripcion: tabla intermedia entre Curso y Estudiante.
"""

import logging

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

logger = logging.getLogger('gestion_academica')


class Inscripcion(models.Model):
    """
    Registro de la inscripcion de un Estudiante en un Curso.

    Tabla intermedia explicita que reemplaza el ManyToMany implicito
    de Django para agregar campos de negocio (estado, nota_final).
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de Aprobacion'
        ACTIVA = 'activa', 'Activa'
        RECHAZADA = 'rechazada', 'Rechazada'
        RETIRADA = 'retirada', 'Retirada'
        COMPLETADA = 'completada', 'Completada'

    curso = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name='Curso',
    )

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscripciones_como_estudiante',
        verbose_name='Estudiante',
        limit_choices_to={'rol': 'estudiante'},
    )

    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
        verbose_name='Estado',
    )

    nota_final = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Nota final',
        help_text='Promedio ponderado de todas las entregas calificadas.',
    )

    fecha_inscripcion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de inscripcion',
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Ultima actualizacion',
    )

    class Meta:
        verbose_name = 'Inscripcion'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-fecha_inscripcion']
        constraints = [
            # Garantia de unicidad a nivel de base de datos:
            # un estudiante no puede estar inscrito dos veces en el mismo curso.
            # UniqueConstraint es preferible a unique_together (deprecated).
            models.UniqueConstraint(
                fields=['curso', 'estudiante'],
                name='unique_inscripcion_curso_estudiante',
            ),
        ]
        indexes = [
            models.Index(
                fields=['estudiante', 'estado'],
                name='idx_inscr_estudiante_estado',
            ),
            models.Index(
                fields=['curso', 'estado'],
                name='idx_inscr_curso_estado',
            ),
        ]

    def __str__(self):
        return f'{self.estudiante.get_full_name() or self.estudiante.username} en {self.curso.nombre}'

    def activar(self):
        """Aprueba y activa la inscripcion."""
        self.estado = self.Estado.ACTIVA
        self.save(update_fields=['estado', 'fecha_actualizacion'])
        logger.info('Inscripcion aprobada y activada. ID: %s', self.pk)

    def rechazar(self):
        """Rechaza la solicitud de inscripcion."""
        self.estado = self.Estado.RECHAZADA
        self.save(update_fields=['estado', 'fecha_actualizacion'])
        logger.info('Inscripcion rechazada. ID: %s', self.pk)

    def retirar(self):
        """Cambia el estado a RETIRADA preservando el historial academico."""
        self.estado = self.Estado.RETIRADA
        self.save(update_fields=['estado', 'fecha_actualizacion'])
        logger.info(
            'Estudiante retirado del curso. Inscripcion ID: %s', self.pk
        )

    def completar(self, nota_final):
        """Marca la inscripcion como completada y registra la nota final."""
        self.estado = self.Estado.COMPLETADA
        self.nota_final = nota_final
        self.save(update_fields=['estado', 'nota_final', 'fecha_actualizacion'])

    def calcular_estadisticas_academicas(self):
        """
        Calcula el progreso del estudiante, promedios de notas y estado academico actual.
        """
        from apps.asignaciones.models import Entrega

        total_planificadas = self.curso.total_asignaciones or 1
        asignaciones_creadas = self.curso.asignaciones.count()

        entregas = Entrega.objects.filter(
            asignacion__curso=self.curso,
            estudiante=self.estudiante
        ).select_related('asignacion')

        total_entregadas = entregas.count()
        entregas_calificadas = [e for e in entregas if e.estado == Entrega.Estado.CALIFICADA and e.calificacion is not None]
        total_calificadas = len(entregas_calificadas)

        porcentaje_avance = round(min(100.0, (total_entregadas / total_planificadas) * 100), 1)

        if total_calificadas > 0:
            puntos_obtenidos_ponderados = sum(
                (float(e.calificacion) / float(e.asignacion.valor_maximo)) * float(e.asignacion.porcentaje or 25.0)
                for e in entregas_calificadas
                if e.asignacion.valor_maximo > 0
            )
            porcentaje_evaluado = sum(
                float(e.asignacion.porcentaje or 25.0)
                for e in entregas_calificadas
            )

            if porcentaje_evaluado > 0:
                promedio_acumulado = round((puntos_obtenidos_ponderados / porcentaje_evaluado) * 20.0, 2)
            else:
                promedio_acumulado = None

            nota_proyectada = round((puntos_obtenidos_ponderados / 100.0) * 20.0, 2)

            if promedio_acumulado is not None and promedio_acumulado >= 13.0:
                rendimiento = 'Aprobando (Satisfactorio)'
            elif promedio_acumulado is not None and promedio_acumulado >= 10.5:
                rendimiento = 'Aprobando (En riesgo)'
            else:
                rendimiento = 'Desaprobando'

            if promedio_acumulado is not None and self.nota_final != promedio_acumulado:
                self.nota_final = promedio_acumulado
                self.save(update_fields=['nota_final'])
        else:
            promedio_acumulado = None
            nota_proyectada = 0.0
            rendimiento = 'Sin evaluaciones calificadas'

        return {
            'total_asignaciones_planificadas': total_planificadas,
            'asignaciones_publicadas': asignaciones_creadas,
            'entregas_enviadas': total_entregadas,
            'entregas_calificadas': total_calificadas,
            'porcentaje_avance': f'{porcentaje_avance}%',
            'promedio_acumulado_base20': promedio_acumulado,
            'nota_proyectada_curso': nota_proyectada,
            'estado_rendimiento': rendimiento,
        }
