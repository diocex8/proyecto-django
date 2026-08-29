"""
Registro del modelo Usuario en el panel de administracion de Django.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Usuario, SolicitudProfesor


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Configuracion del admin para el modelo Usuario personalizado.
    Extiende UserAdmin para conservar la funcionalidad de cambio de contrasena
    que Django provee por defecto para sus modelos de usuario.
    """

    # Columnas visibles en la lista de usuarios
    list_display = ('email', 'get_full_name', 'rol', 'is_active', 'bloqueado_hasta', 'fecha_registro')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'username')
    ordering = ('-fecha_registro',)
    actions = ['desbloquear_usuarios']

    # Campos que se muestran al editar un usuario existente
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Informacion personal'), {'fields': ('first_name', 'last_name')}),
        (_('Rol del sistema'), {'fields': ('rol',)}),
        (_('Seguridad y Penalizaciones'), {'fields': ('bloqueado_hasta', 'intentos_fallidos_creacion')}),
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

    @admin.action(description='Desbloquear usuarios seleccionados')
    def desbloquear_usuarios(self, request, queryset):
        queryset.update(bloqueado_hasta=None, intentos_fallidos_creacion=0)
        self.message_user(request, f'Se han desbloqueado {queryset.count()} usuario(s).')


@admin.register(SolicitudProfesor)
class SolicitudProfesorAdmin(admin.ModelAdmin):
    """
    Panel de administracion para gestionar las solicitudes de registro de profesores.
    Permite a los administradores aceptar o rechazar solicitudes con un solo clic.
    """
    list_display = (
        'usuario',
        'email',
        'estado',
        'fecha_solicitud',
        'fecha_resolucion',
        'cooldown_estado',
    )
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('email', 'usuario__first_name', 'usuario__last_name', 'usuario__username')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('fecha_solicitud', 'fecha_resolucion')
    actions = ['aceptar_solicitudes', 'rechazar_solicitudes']

    @admin.display(description='Estado Cooldown (2h)')
    def cooldown_estado(self, obj):
        if obj.esta_en_cooldown():
            return f'Bloqueado ({obj.tiempo_restante_cooldown()} min restantes)'
        elif obj.estado == SolicitudProfesor.Estado.RECHAZADA:
            return 'Cooldown expirado (re-registro permitido)'
        return '-'

    @admin.action(description='Aceptar solicitudes de profesor seleccionadas')
    def aceptar_solicitudes(self, request, queryset):
        total = 0
        for solicitud in queryset:
            solicitud.aceptar()
            total += 1
        self.message_user(
            request,
            f'Se han aceptado {total} solicitud(es) de profesor y activado sus cuentas.'
        )

    @admin.action(description='Rechazar solicitudes de profesor seleccionadas')
    def rechazar_solicitudes(self, request, queryset):
        total = 0
        for solicitud in queryset:
            solicitud.rechazar(motivo='Rechazada por administrador desde el panel.')
            total += 1
        self.message_user(
            request,
            f'Se han rechazado {total} solicitud(es) de profesor. El bloqueo de 2 horas ha comenzado.'
        )
