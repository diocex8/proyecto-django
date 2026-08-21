"""
apps/asignaciones/models.py

Modelos de Asignacion y Entrega del dominio academico.

Decision de arquitectura:
    Asignacion y Entrega se mantienen en la misma aplicacion porque son
    conceptos acoplados: una Entrega no existe sin una Asignacion.
    Separarlos en dos apps introduciria complejidad innecesaria y
    dependencias circulares.

    La calificacion se almacena en la Entrega (no en la Inscripcion)
    porque una inscripcion puede tener multiples entregas (una por
    asignacion), y cada entrega tiene su propia nota.
"""

import logging

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger('gestion_academica')


class Asignacion(models.Model):
    """
    Tarea, examen o proyecto creado por un Profesor dentro de un Curso.

    Una Asignacion pertenece a un Curso especifico y define las reglas
    de entrega: fecha limite, valor maximo y tipo.
    """

    class Tipo(models.TextChoices):
        TAREA = 'tarea', 'Tarea'
        EXAMEN = 'examen', 'Examen'
        PROYECTO = 'proyecto', 'Proyecto'
        QUIZ = 'quiz', 'Quiz'

    curso = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.CASCADE,
        related_name='asignaciones',
        verbose_name='Curso',
    )

    titulo = models.CharField(
        max_length=250,
        verbose_name='Titulo',
    )

    descripcion = models.TextField(
        verbose_name='Descripcion',
        help_text='Instrucciones detalladas de la asignacion.',
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.TAREA,
        db_index=True,
        verbose_name='Tipo',
    )

    valor_maximo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name='Valor maximo',
        help_text='Puntuacion maxima posible para esta asignacion.',
    )

    fecha_entrega = models.DateTimeField(
        verbose_name='Fecha limite de entrega',
    )

    permite_entrega_tardia = models.BooleanField(
        default=False,
        verbose_name='Permite entrega tardia',
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creacion',
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Ultima actualizacion',
    )

    class Meta:
        verbose_name = 'Asignacion'
        verbose_name_plural = 'Asignaciones'
        ordering = ['fecha_entrega']
        indexes = [
            models.Index(
                fields=['curso', 'tipo'],
                name='idx_asignacion_curso_tipo',
            ),
            models.Index(
                fields=['curso', 'fecha_entrega'],
                name='idx_asignacion_curso_fecha',
            ),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo} ({self.curso.codigo})'

    @property
    def esta_vencida(self):
        """Indica si la fecha de entrega ya paso."""
        return timezone.now() > self.fecha_entrega

    @property
    def acepta_entregas(self):
        """
        Determina si la asignacion acepta nuevas entregas.
        Considera si permite entrega tardia o si aun esta dentro del plazo.
        """
        if not self.esta_vencida:
            return True
        return self.permite_entrega_tardia


class Entrega(models.Model):
    """
    Entrega de un Estudiante para una Asignacion especifica.

    Reglas de negocio implementadas a nivel de modelo:
    - Un estudiante solo puede entregar una vez por asignacion (UniqueConstraint).
    - La calificacion solo puede ser asignada por el profesor del curso.
    - La nota no puede exceder el valor_maximo de la asignacion.
    """

    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        ENVIADA = 'enviada', 'Enviada'
        CALIFICADA = 'calificada', 'Calificada'
        DEVUELTA = 'devuelta', 'Devuelta para revision'

    asignacion = models.ForeignKey(
        Asignacion,
        on_delete=models.CASCADE,
        related_name='entregas',
        verbose_name='Asignacion',
    )

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='entregas_como_estudiante',
        verbose_name='Estudiante',
        limit_choices_to={'rol': 'estudiante'},
    )

    contenido = models.TextField(
        verbose_name='Contenido de la entrega',
        help_text='Respuesta, solucion o enlace al trabajo entregado.',
    )

    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
        verbose_name='Estado',
    )

    calificacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='Calificacion',
        help_text='Nota asignada por el profesor. No puede superar el valor maximo.',
    )

    retroalimentacion = models.TextField(
        blank=True,
        verbose_name='Retroalimentacion del profesor',
    )

    fecha_entrega = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de entrega',
    )

    fecha_calificacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de calificacion',
    )

    class Meta:
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'
        ordering = ['-fecha_entrega']
        constraints = [
            # Un estudiante no puede entregar dos veces la misma asignacion.
            models.UniqueConstraint(
                fields=['asignacion', 'estudiante'],
                name='uq_entrega_asignacion_estudiante',
            ),
        ]
        indexes = [
            models.Index(
                fields=['asignacion', 'estado'],
                name='idx_entrega_asignacion_estado',
            ),
            models.Index(
                fields=['estudiante', 'estado'],
                name='idx_entrega_estudiante_estado',
            ),
        ]

    def __str__(self):
        return (
            f'Entrega de {self.estudiante.get_full_name()} '
            f'para "{self.asignacion.titulo}"'
        )

    def calificar(self, nota, retroalimentacion=''):
        """
        Metodo de negocio: califica la entrega con validacion de rango.

        La logica de negocio vive en el modelo para que sea reutilizable
        desde la vista, desde el admin y desde tareas programadas.
        """
        valor_maximo = self.asignacion.valor_maximo
        if nota > valor_maximo:
            raise ValueError(
                f'La calificacion ({nota}) no puede superar el valor '
                f'maximo de la asignacion ({valor_maximo}).'
            )
        if nota < 0:
            raise ValueError('La calificacion no puede ser negativa.')

        self.calificacion = nota
        self.retroalimentacion = retroalimentacion
        self.estado = self.Estado.CALIFICADA
        self.fecha_calificacion = timezone.now()
        self.save(update_fields=[
            'calificacion', 'retroalimentacion', 'estado', 'fecha_calificacion'
        ])
        logger.info(
            'Entrega calificada. ID: %s, Nota: %s/%s',
            self.pk, nota, valor_maximo
        )
