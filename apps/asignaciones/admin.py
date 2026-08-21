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
    list_display = ('titulo', 'curso', 'tipo', 'valor_maximo', 'fecha_entrega', 'esta_vencida')
    list_filter = ('tipo', 'permite_entrega_tardia')
    search_fields = ('titulo', 'curso__codigo')
    ordering = ('fecha_entrega',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    raw_id_fields = ('curso',)
    list_select_related = ('curso',)
    inlines = [EntregaInline]

    @admin.display(boolean=True, description='Vencida')
    def esta_vencida(self, obj):
        return obj.esta_vencida


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'asignacion', 'estado', 'calificacion', 'fecha_entrega')
    list_filter = ('estado',)
    search_fields = ('estudiante__email', 'asignacion__titulo')
    ordering = ('-fecha_entrega',)
    readonly_fields = ('fecha_entrega', 'fecha_calificacion')
    raw_id_fields = ('estudiante', 'asignacion')
    list_select_related = ('estudiante', 'asignacion', 'asignacion__curso')
