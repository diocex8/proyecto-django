"""apps/cursos/admin.py"""
from django.contrib import admin
from .models import Curso


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'profesor', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado', 'fecha_inicio')
    search_fields = ('codigo', 'nombre', 'profesor__email')
    ordering = ('-fecha_creacion',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    raw_id_fields = ('profesor',)
    list_select_related = ('profesor',)
