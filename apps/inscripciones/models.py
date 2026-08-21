"""
apps/inscripciones/models.py

Modelo de inscripcion: tabla intermedia personalizada entre Curso y Estudiante.

Decision de arquitectura:
    Django permite una ManyToManyField simple con `through=` para tablas
    intermedias. Se usa un modelo explicito (en lugar del ManyToMany implicito)
    porque necesitamos campos adicionales: estado, fecha_inscripcion y
    nota_final. Un ManyToMany implicito no permite agregar estos campos.

    Patron: la tabla Inscripcion es el registro "contable" de que un
    estudiante pertenece a un curso. Modificarla (ej. dar de baja) no
    elimina el registro sino que cambia su estado (soft-delete logico
    por estado) para preservar la auditoria.
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
        ACTIVA = 'activa', 'Activa'
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
        default=Estado.ACTIVA,
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
                name='uq_inscripcion_curso_estudiante',
            ),
        ]
        indexes = [
            models.Index(
                fields=['estudiante', 'estado'],
                name='idx_inscr_est_estado',
            ),
            models.Index(
                fields=['curso', 'estado'],
                name='idx_inscr_curso_estado',
            ),
        ]

    def __str__(self):
        return f'{self.estudiante.get_full_name()} en {self.curso.nombre}'

    def retirar(self):
        """
        Metodo de negocio: cambia el estado a RETIRADA en lugar de eliminar.
        Esto preserva el historial academico del estudiante.
        """
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
