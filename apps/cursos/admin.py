from django.contrib import admin
from .models import Curso


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'profesor', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado', 'fecha_inicio')
    search_fields = ('codigo', 'nombre', 'profesor__email')
    ordering = ('-fecha_creacion',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    autocomplete_fields = ('profesor',)
    list_select_related = ('profesor',)
    actions = ['aprobar_cursos']

    @admin.action(description='Aprobar cursos pendientes (Cambiar a Borrador)')
    def aprobar_cursos(self, request, queryset):
        pendientes = queryset.filter(estado=Curso.Estado.PENDIENTE)
        total = pendientes.update(estado=Curso.Estado.BORRADOR)
        self.message_user(request, f'Se han aprobado {total} curso(s). Ya pueden ser editados por sus profesores.')
