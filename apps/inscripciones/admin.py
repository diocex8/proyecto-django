from django.contrib import admin
from .models import Inscripcion


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'curso', 'estado', 'nota_final', 'fecha_inscripcion')
    list_filter = ('estado',)
    search_fields = ('estudiante__email', 'curso__codigo', 'curso__nombre')
    ordering = ('-fecha_inscripcion',)
    readonly_fields = ('fecha_inscripcion', 'fecha_actualizacion')
    autocomplete_fields = ('estudiante', 'curso')
    list_select_related = ('estudiante', 'curso')
