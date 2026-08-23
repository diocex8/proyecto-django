"""
apps/usuarios/models.py

Modelo de usuario personalizado del proyecto.
"""

from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone



class Usuario(AbstractUser):
    """
    Modelo de usuario base del sistema.

    Extiende AbstractUser para agregar campos especificos del dominio
    academico como el rol del usuario dentro del sistema.
    """

    class Rol(models.TextChoices):
        """
        Enum de roles disponibles en el sistema.

        Se usa TextChoices en lugar de IntegerChoices para que la base
        de datos almacene valores legibles ('profesor', 'estudiante')
        en lugar de enteros opacos (1, 2). Esto facilita la depuracion
        y las consultas directas a la base de datos.
        """
        PROFESOR = 'profesor', 'Profesor'
        ESTUDIANTE = 'estudiante', 'Estudiante'
        ADMINISTRADOR = 'administrador', 'Administrador'

    # Campo de email unico y obligatorio (AbstractUser lo tiene pero no
    # lo define como UNIQUE por defecto)
    email = models.EmailField(
        unique=True,
        verbose_name='Correo electronico',
        help_text='Direccion de correo electronico unica del usuario.',
    )

    rol = models.CharField(
        max_length=15,
        choices=Rol.choices,
        default=Rol.ESTUDIANTE,
        db_index=True,  # Se filtra frecuentemente por rol en las vistas
        verbose_name='Rol',
        help_text='Rol del usuario dentro del sistema academico.',
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )

    ultima_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Ultima actualizacion',
    )

    # Usar email como campo de autenticacion en lugar de username
    USERNAME_FIELD = 'email'

    # username sigue siendo obligatorio pero no se usa para autenticar
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['rol', 'is_active'], name='idx_usuario_rol_activo'),
        ]

    def __str__(self):
        return f'{self.get_full_name()} ({self.email}) - {self.get_rol_display()}'

    @property
    def es_profesor(self):
        """Propiedad de conveniencia para verificar el rol sin comparar strings."""
        return self.rol == self.Rol.PROFESOR

    @property
    def es_estudiante(self):
        """Propiedad de conveniencia para verificar el rol."""
        return self.rol == self.Rol.ESTUDIANTE

    @property
    def es_administrador(self):
        """Propiedad de conveniencia para verificar el rol."""
        return self.rol == self.Rol.ADMINISTRADOR


class SolicitudProfesor(models.Model):
    """
    Gestiona las solicitudes de registro para cuentas con rol Profesor.
    
    Reglas de negocio:
    - Las cuentas de profesor se crean inactivas hasta ser aprobadas por un administrador.
    - Solo se permite una solicitud de profesor por cuenta.
    - Si es rechazada, se aplica un bloqueo de re-registro de 2 horas.
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ACEPTADA = 'aceptada', 'Aceptada'
        RECHAZADA = 'rechazada', 'Rechazada'

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitud_profesor',
        verbose_name='Usuario solicitante',
    )
    email = models.EmailField(
        db_index=True,
        verbose_name='Correo electronico',
        help_text='Correo asociado a la solicitud para control de reintentos.',
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
        verbose_name='Estado de la solicitud',
    )
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de solicitud',
    )
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de resolucion',
    )
    motivo_rechazo = models.TextField(
        blank=True,
        default='',
        verbose_name='Motivo de rechazo o comentarios',
    )

    class Meta:
        verbose_name = 'Solicitud de Profesor'
        verbose_name_plural = 'Solicitudes de Profesores'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'Solicitud de {self.usuario.get_full_name() or self.email} - {self.get_estado_display()}'

    def esta_en_cooldown(self):
        """
        Verifica si la solicitud fue rechazada y aun se encuentra dentro de las 2 horas de bloqueo.
        """
        if self.estado != self.Estado.RECHAZADA or not self.fecha_resolucion:
            return False
        return timezone.now() < (self.fecha_resolucion + timedelta(hours=2))

    def tiempo_restante_cooldown(self):
        """
        Calcula el tiempo restante en minutos para que expire el bloqueo de 2 horas.
        """
        if not self.esta_en_cooldown():
            return 0
        tiempo_fin = self.fecha_resolucion + timedelta(hours=2)
        diferencia = tiempo_fin - timezone.now()
        return max(1, int(diferencia.total_seconds() // 60))

    def aceptar(self):
        """Aprueba la solicitud y activa la cuenta del usuario para permitir el login."""
        self.estado = self.Estado.ACEPTADA
        self.fecha_resolucion = timezone.now()
        self.save(update_fields=['estado', 'fecha_resolucion'])
        self.usuario.is_active = True
        self.usuario.save(update_fields=['is_active'])

    def rechazar(self, motivo=''):
        """Rechaza la solicitud, desactiva al usuario e inicia el periodo de 2 horas de bloqueo."""
        self.estado = self.Estado.RECHAZADA
        self.fecha_resolucion = timezone.now()
        if motivo:
            self.motivo_rechazo = motivo
        self.save(update_fields=['estado', 'fecha_resolucion', 'motivo_rechazo'])
        self.usuario.is_active = False
        self.usuario.save(update_fields=['is_active'])
