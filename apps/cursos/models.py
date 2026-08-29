"""
Modelos del dominio de cursos academicos.
"""

import logging

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger('gestion_academica')


class CursoQuerySet(models.QuerySet):
    """
    QuerySet personalizado para el modelo Curso.

    Centraliza los filtros mas comunes para evitar duplicar logica
    de consulta en multiples vistas. Es el patron "Fat QuerySet".
    """

    def publicados(self):
        return self.filter(estado=Curso.Estado.PUBLICADO)

    def del_profesor(self, profesor):
        return self.filter(profesor=profesor)

    def con_relaciones(self):
        """
        Pre-carga todas las relaciones necesarias para evitar N+1.
        Este metodo debe llamarse en TODOS los get_queryset() de las vistas.
        """
        return self.select_related('profesor').prefetch_related('inscripciones__estudiante')


class CursoManager(models.Manager):
    """Manager personalizado que usa CursoQuerySet como base."""

    def get_queryset(self):
        return CursoQuerySet(self.model, using=self._db)

    def publicados(self):
        return self.get_queryset().publicados()

    def del_profesor(self, profesor):
        return self.get_queryset().del_profesor(profesor)

    def con_relaciones(self):
        return self.get_queryset().con_relaciones()


class Curso(models.Model):
    """
    Representa un curso academico creado por un Profesor.

    Un curso puede tener muchos estudiantes (via Inscripcion)
    y muchas asignaciones (via Asignacion).
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de Aprobacion'
        BORRADOR = 'borrador', 'Borrador'
        PUBLICADO = 'publicado', 'Publicado'
        ARCHIVADO = 'archivado', 'Archivado'

    profesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        # no se puede eliminar un usuario
        # tiene cursos activos. Esto evita borrados en cascada accidentales.
        related_name='cursos_como_profesor',
        verbose_name='Profesor',
        limit_choices_to={'rol': 'profesor'},
    )

    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre del curso',
        db_index=True,  # Se busca frecuentemente por nombre
    )

    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripcion',
    )

    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Codigo del curso',
        help_text='Codigo unico de identificacion del curso (ej. MAT-101).',
    )

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
        verbose_name='Estado',
    )

    capacidad_maxima = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name='Capacidad maxima de estudiantes',
    )

    total_asignaciones = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        verbose_name='Total de asignaciones planificadas',
        help_text='Cantidad total de asignaciones planificadas para calcular el progreso y promedios del curso.',
    )

    fecha_inicio = models.DateField(
        verbose_name='Fecha de inicio',
    )

    fecha_fin = models.DateField(
        verbose_name='Fecha de finalizacion',
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creacion',
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Ultima actualizacion',
    )

    # Manager personalizado como manager principal
    objects = CursoManager()

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['-fecha_creacion']
        indexes = [
            # Indice compuesto para la consulta mas frecuente:
            # "listar cursos publicados de un profesor"
            models.Index(
                fields=['profesor', 'estado'],
                name='idx_curso_profesor_estado',
            ),
            models.Index(
                fields=['estado', 'fecha_inicio'],
                name='idx_curso_estado_inicio',
            ),
        ]
        constraints = [
            # Validacion a nivel de base de datos: fecha_fin debe ser
            # posterior a fecha_inicio. No depende solo del serializador.
            models.CheckConstraint(
                condition=models.Q(fecha_fin__gt=models.F('fecha_inicio')),
                name='chk_curso_fecha_fin_mayor_inicio',
            ),
        ]

    def __str__(self):
        cupos = self.cupos_disponibles
        return f'[{self.codigo}] {self.nombre} (Cupos disponibles: {cupos}/{self.capacidad_maxima})'

    @property
    def esta_activo(self):
        """Determina si el curso esta actualmente en curso segun las fechas."""
        hoy = timezone.now().date()
        return (
            self.estado == self.Estado.PUBLICADO
            and self.fecha_inicio <= hoy <= self.fecha_fin
        )

    @property
    def cupos_disponibles(self):
        """
        Calcula los cupos disponibles. Usa annotate() en la vista
        para evitar N+1; esta propiedad es solo de conveniencia.
        """
        return self.capacidad_maxima - self.inscripciones.filter(
            estado='activa'
        ).count()

    def publicar(self):
        """Publica el curso si no esta archivado."""
        if self.estado == self.Estado.ARCHIVADO:
            raise ValueError('No se puede publicar un curso archivado.')
        self.estado = self.Estado.PUBLICADO
        self.save(update_fields=['estado', 'fecha_actualizacion'])
        logger.info('Curso publicado. ID: %s, Codigo: %s', self.pk, self.codigo)

    def archivar(self):
        """Archiva el curso."""
        self.estado = self.Estado.ARCHIVADO
        self.save(update_fields=['estado', 'fecha_actualizacion'])
        logger.info('Curso archivado. ID: %s', self.pk)
