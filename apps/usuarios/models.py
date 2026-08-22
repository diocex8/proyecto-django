"""
apps/usuarios/models.py

Modelo de usuario personalizado del proyecto.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


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
