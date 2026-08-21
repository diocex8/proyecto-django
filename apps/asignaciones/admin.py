"""apps/asignaciones/admin.py"""
from django.contrib import admin
from .models import Asignacion, Entrega


class EntregaInline(admin.TabularInline):
    model = Entrega
    extra = 0
    readonly_fields = ('estudiante', 'fecha_entrega', 'estado', 'calificacion')
    can_delete = False


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'obtener_profesor', 'tipo', 'valor_maximo', 'fecha_entrega', 'esta_vencida')
    list_filter = ('curso', 'curso__profesor', 'tipo', 'permite_entrega_tardia', 'fecha_entrega')
    search_fields = ('titulo', 'descripcion', 'curso__nombre', 'curso__codigo', 'curso__profesor__email', 'curso__profesor__username')
    ordering = ('-fecha_entrega',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    autocomplete_fields = ('curso',)
    list_select_related = ('curso', 'curso__profesor')
    inlines = [EntregaInline]

    @admin.display(boolean=True, description='Vencida')
    def esta_vencida(self, obj):
        return obj.esta_vencida

    @admin.display(description='Profesor')
    def obtener_profesor(self, obj):
        return obj.curso.profesor


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'asignacion', 'obtener_curso', 'estado', 'calificacion', 'fecha_entrega')
    list_filter = ('asignacion__curso', 'estado', 'asignacion__tipo', 'estudiante')
    search_fields = ('estudiante__email', 'estudiante__username', 'estudiante__first_name', 'estudiante__last_name', 'asignacion__titulo', 'asignacion__curso__codigo', 'asignacion__curso__nombre')
    ordering = ('-fecha_entrega',)
    readonly_fields = ('fecha_entrega', 'fecha_calificacion')
    autocomplete_fields = ('estudiante', 'asignacion')
    list_select_related = ('estudiante', 'asignacion', 'asignacion__curso')

    @admin.display(description='Curso')
    def obtener_curso(self, obj):
        return obj.asignacion.curso

