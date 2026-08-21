"""
apps/usuarios/admin.py

Registro del modelo Usuario en el panel de administracion de Django.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Configuracion del admin para el modelo Usuario personalizado.
    Extiende UserAdmin para conservar la funcionalidad de cambio de contrasena
    que Django provee por defecto para sus modelos de usuario.
    """

    # Columnas visibles en la lista de usuarios
    list_display = ('email', 'get_full_name', 'rol', 'is_active', 'fecha_registro')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'username')
    ordering = ('-fecha_registro',)

    # Campos que se muestran al editar un usuario existente
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Informacion personal'), {'fields': ('first_name', 'last_name')}),
        (_('Rol del sistema'), {'fields': ('rol',)}),
        (_('Permisos'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Fechas'), {'fields': ('last_login',)}),
    )

    # Campos que se muestran al crear un usuario nuevo
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'rol', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('fecha_registro', 'ultima_actualizacion')
