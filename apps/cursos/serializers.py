"""
Serializadores del dominio de cursos.
"""

from django.db.models import Count
from rest_framework import serializers

from apps.usuarios.serializers import UsuarioResumenSerializer
from .models import Curso


class CursoListaSerializer(serializers.ModelSerializer):
    """
    Serializador compacto para el listado de cursos.
    Incluye datos del profesor (anidado) y conteos calculados.
    """
    profesor = UsuarioResumenSerializer(read_only=True)
    total_inscritos = serializers.SerializerMethodField()
    asignaciones_creadas = serializers.SerializerMethodField()
    esta_activo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Curso
        fields = (
            'id', 'codigo', 'nombre', 'descripcion', 'estado',
            'profesor', 'capacidad_maxima', 'total_inscritos',
            'total_asignaciones', 'asignaciones_creadas',
            'fecha_inicio', 'fecha_fin', 'esta_activo',
        )
        read_only_fields = fields

    def get_total_inscritos(self, obj):
        if hasattr(obj, 'total_inscritos_anotado'):
            return obj.total_inscritos_anotado
        return obj.inscripciones.filter(estado='activa').count()

    def get_asignaciones_creadas(self, obj):
        if hasattr(obj, 'total_asignaciones_anotado'):
            return obj.total_asignaciones_anotado
        return obj.asignaciones.count()


class CursoDetalleSerializer(serializers.ModelSerializer):
    """
    Serializador completo para el detalle de un curso.
    Incluye datos del profesor anidados.
    """
    profesor = UsuarioResumenSerializer(read_only=True)
    total_inscritos = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()
    asignaciones_creadas = serializers.SerializerMethodField()
    esta_activo = serializers.SerializerMethodField()

    class Meta:
        model = Curso
        fields = (
            'id', 'codigo', 'nombre', 'descripcion', 'estado',
            'profesor', 'capacidad_maxima', 'total_asignaciones',
            'asignaciones_creadas', 'total_inscritos',
            'cupos_disponibles', 'fecha_inicio', 'fecha_fin',
            'esta_activo', 'fecha_creacion', 'fecha_actualizacion',
        )
        read_only_fields = fields

    def get_total_inscritos(self, obj):
        if hasattr(obj, 'total_inscritos_anotado'):
            return obj.total_inscritos_anotado
        return obj.inscripciones.filter(estado='activa').count()

    def get_cupos_disponibles(self, obj):
        total_inscritos = self.get_total_inscritos(obj)
        return max(0, obj.capacidad_maxima - total_inscritos)

    def get_asignaciones_creadas(self, obj):
        return obj.asignaciones.count()

    def get_esta_activo(self, obj):
        return obj.esta_activo


class CursoCrearActualizarSerializer(serializers.ModelSerializer):
    """
    Serializador plano para CREAR y ACTUALIZAR un curso.
    """

    class Meta:
        model = Curso
        fields = (
            'codigo', 'nombre', 'descripcion',
            'capacidad_maxima', 'total_asignaciones',
            'fecha_inicio', 'fecha_fin',
        )

    def validate_codigo(self, value):
        """Validacion de unicidad excluyendo la instancia actual (para updates)."""
        qs = Curso.objects.filter(codigo=value.upper())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f'Ya existe un curso con el codigo "{value}".'
            )
        return value.upper()

    def validate(self, attrs):
        """Validacion cruzada de fechas."""
        fecha_inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fecha_fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha de finalizacion debe ser posterior a la fecha de inicio.'
            })
        return attrs

    def create(self, validated_data):
        """Asigna el profesor desde el usuario autenticado de la peticion."""
        profesor = self.context['request'].user
        return Curso.objects.create(profesor=profesor, **validated_data)


class CambiarEstadoCursoSerializer(serializers.Serializer):
    """
    Serializador para el endpoint de cambio de estado de un curso.
    Valida que la transicion de estado sea valida segun las reglas de negocio.
    """
    TRANSICIONES_VALIDAS = {
        Curso.Estado.BORRADOR: [Curso.Estado.PUBLICADO],
        Curso.Estado.PUBLICADO: [Curso.Estado.ARCHIVADO, Curso.Estado.BORRADOR],
        Curso.Estado.ARCHIVADO: [],
    }

    nuevo_estado = serializers.ChoiceField(choices=Curso.Estado.choices)

    def validate_nuevo_estado(self, value):
        curso = self.context['curso']
        transiciones_permitidas = self.TRANSICIONES_VALIDAS.get(curso.estado, [])
        if value not in transiciones_permitidas:
            raise serializers.ValidationError(
                f'No se puede cambiar el estado de "{curso.get_estado_display()}" '
                f'a "{dict(Curso.Estado.choices).get(value)}". '
                f'Transiciones validas: {[dict(Curso.Estado.choices).get(t) for t in transiciones_permitidas] or "ninguna"}.'
            )
        return value
