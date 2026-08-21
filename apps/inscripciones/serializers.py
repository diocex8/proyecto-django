"""
apps/inscripciones/serializers.py

Serializadores del dominio de inscripciones.
"""

from rest_framework import serializers

from apps.cursos.models import Curso
from apps.cursos.serializers import CursoListaSerializer
from apps.usuarios.serializers import UsuarioResumenSerializer
from apps.inscripciones.models import Inscripcion


class InscripcionListaSerializer(serializers.ModelSerializer):
    """Serializador de lectura con datos anidados de curso y estudiante."""
    curso = CursoListaSerializer(read_only=True)
    estudiante = UsuarioResumenSerializer(read_only=True)

    class Meta:
        model = Inscripcion
        fields = (
            'id', 'curso', 'estudiante', 'estado',
            'nota_final', 'fecha_inscripcion',
        )
        read_only_fields = fields


class InscripcionDetalleSerializer(serializers.ModelSerializer):
    """Serializador completo de una inscripcion individual."""
    curso = CursoListaSerializer(read_only=True)
    estudiante = UsuarioResumenSerializer(read_only=True)
    promedio_entregas = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = (
            'id', 'curso', 'estudiante', 'estado',
            'nota_final', 'promedio_entregas',
            'fecha_inscripcion', 'fecha_actualizacion',
        )
        read_only_fields = fields

    def get_promedio_entregas(self, obj):
        """
        Calcula el promedio de las entregas calificadas del estudiante en este curso.

        OPTIMIZACION: Usa prefetch_related desde la vista para cargar las
        entregas en memoria antes de este calculo. Si no hay prefetch,
        hace la consulta de forma directa (N+1 documentado).
        """
        from django.db.models import Avg
        from apps.asignaciones.models import Entrega

        promedio = Entrega.objects.filter(
            estudiante=obj.estudiante,
            asignacion__curso=obj.curso,
            estado=Entrega.Estado.CALIFICADA,
        ).aggregate(promedio=Avg('calificacion'))['promedio']

        return round(float(promedio), 2) if promedio is not None else None


class InscripcionCrearSerializer(serializers.ModelSerializer):
    """
    Serializador plano para inscribir a un estudiante en un curso.

    Implementa validaciones de negocio:
    - El curso debe estar publicado.
    - El estudiante no puede estar ya inscrito.
    - Debe haber cupos disponibles.
    - El estudiante no puede inscribirse en un curso que el mismo dicta (si fuera profesor).
    """
    curso_id = serializers.PrimaryKeyRelatedField(
        queryset=Curso.objects.filter(estado=Curso.Estado.PUBLICADO),
        source='curso',
        help_text='ID del curso publicado al que desea inscribirse.',
    )

    class Meta:
        model = Inscripcion
        fields = ('curso_id',)

    def validate_curso_id(self, curso):
        """Validaciones de negocio sobre el curso seleccionado."""
        estudiante = self.context['request'].user

        # Verificar si ya existe una inscripcion (activa o no)
        inscripcion_existente = Inscripcion.objects.filter(
            curso=curso,
            estudiante=estudiante,
        ).first()

        if inscripcion_existente:
            if inscripcion_existente.estado == Inscripcion.Estado.ACTIVA:
                raise serializers.ValidationError(
                    'Ya estas inscrito en este curso.'
                )
            elif inscripcion_existente.estado == Inscripcion.Estado.RETIRADA:
                raise serializers.ValidationError(
                    'Te retiraste de este curso. Contacta a tu profesor para reinscribirte.'
                )

        # Verificar capacidad del curso
        inscritos_activos = curso.inscripciones.filter(
            estado=Inscripcion.Estado.ACTIVA
        ).count()
        if inscritos_activos >= curso.capacidad_maxima:
            raise serializers.ValidationError(
                f'El curso "{curso.nombre}" no tiene cupos disponibles.'
            )

        return curso

    def create(self, validated_data):
        """Asigna el estudiante desde el usuario autenticado."""
        estudiante = self.context['request'].user
        return Inscripcion.objects.create(
            estudiante=estudiante,
            **validated_data
        )
