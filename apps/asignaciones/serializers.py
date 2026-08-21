"""
apps/asignaciones/serializers.py

Serializadores del dominio de asignaciones y entregas.
"""

from rest_framework import serializers

from apps.cursos.models import Curso
from apps.usuarios.serializers import UsuarioResumenSerializer
from .models import Asignacion, Entrega


# ===========================================================================
# Serializadores de ASIGNACION
# ===========================================================================

class AsignacionListaSerializer(serializers.ModelSerializer):
    """Serializador compacto para listados de asignaciones."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    esta_vencida = serializers.BooleanField(read_only=True)
    acepta_entregas = serializers.BooleanField(read_only=True)
    total_entregas = serializers.SerializerMethodField()
    url_entrega = serializers.SerializerMethodField()

    class Meta:
        model = Asignacion
        fields = (
            'id', 'titulo', 'tipo', 'tipo_display', 'valor_maximo',
            'fecha_entrega', 'esta_vencida', 'acepta_entregas',
            'permite_entrega_tardia', 'total_entregas', 'url_entrega',
        )
        read_only_fields = fields

    def get_total_entregas(self, obj):
        if hasattr(obj, 'total_entregas_anotado'):
            return obj.total_entregas_anotado
        return obj.entregas.count()

    def get_url_entrega(self, obj):
        return f"/api/v1/asignaciones/{obj.id}/entregas/"


class AsignacionDetalleSerializer(serializers.ModelSerializer):
    """Serializador completo con toda la informacion de la asignacion."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    esta_vencida = serializers.SerializerMethodField()
    acepta_entregas = serializers.SerializerMethodField()
    curso_codigo = serializers.CharField(source='curso.codigo', read_only=True)
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)
    url_entrega = serializers.SerializerMethodField()

    class Meta:
        model = Asignacion
        fields = (
            'id', 'curso_codigo', 'curso_nombre', 'titulo', 'descripcion',
            'tipo', 'tipo_display', 'valor_maximo', 'fecha_entrega',
            'esta_vencida', 'acepta_entregas', 'permite_entrega_tardia',
            'url_entrega', 'fecha_creacion', 'fecha_actualizacion',
        )
        read_only_fields = fields

    def get_esta_vencida(self, obj):
        return obj.esta_vencida

    def get_acepta_entregas(self, obj):
        return obj.acepta_entregas

    def get_url_entrega(self, obj):
        return f"/api/v1/asignaciones/{obj.id}/entregas/"


class AsignacionCrearActualizarSerializer(serializers.ModelSerializer):
    """
    Serializador para crear y actualizar asignaciones.
    Permite seleccionar el curso directamente desde el formulario HTML/JSON
    o recibirlo a traves del contexto de la vista.
    """
    curso = serializers.PrimaryKeyRelatedField(
        queryset=Curso.objects.all(),
        required=False,
        help_text='Curso al que pertenece la asignación.',
    )

    class Meta:
        model = Asignacion
        fields = (
            'curso', 'titulo', 'descripcion', 'tipo',
            'valor_maximo', 'fecha_entrega', 'permite_entrega_tardia',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request.user, 'es_profesor', False):
            self.fields['curso'].queryset = Curso.objects.filter(profesor=request.user)

    def validate_fecha_entrega(self, value):
        """La fecha de entrega debe ser futura al momento de crear la asignacion."""
        from django.utils import timezone
        if self.instance is None and value <= timezone.now():
            raise serializers.ValidationError(
                'La fecha de entrega debe ser una fecha futura.'
            )
        return value

    def validate_valor_maximo(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'El valor maximo debe ser mayor a cero.'
            )
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        curso = attrs.get('curso') or self.context.get('curso')

        if not curso and self.instance is None:
            raise serializers.ValidationError({
                'curso': 'Debes seleccionar el curso al que pertenece la asignación.'
            })

        if curso and request and getattr(request.user, 'es_profesor', False):
            if curso.profesor != request.user:
                raise serializers.ValidationError({
                    'curso': 'Solo puedes crear asignaciones en tus propios cursos.'
                })

        return attrs

    def create(self, validated_data):
        curso = validated_data.pop('curso', None) or self.context.get('curso')
        return Asignacion.objects.create(curso=curso, **validated_data)


# ===========================================================================
# Serializadores de ENTREGA
# ===========================================================================

class EntregaListaSerializer(serializers.ModelSerializer):
    """Serializador compacto para listado de entregas."""
    estudiante = UsuarioResumenSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    asignacion_titulo = serializers.CharField(source='asignacion.titulo', read_only=True)
    url_calificar = serializers.SerializerMethodField()
    url_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Entrega
        fields = (
            'id', 'asignacion_titulo', 'estudiante', 'estado',
            'estado_display', 'calificacion', 'fecha_entrega',
            'url_calificar', 'url_detalle',
        )
        read_only_fields = fields

    def get_url_calificar(self, obj):
        return f"/api/v1/asignaciones/{obj.asignacion_id}/entregas/{obj.id}/calificar/"

    def get_url_detalle(self, obj):
        return f"/api/v1/asignaciones/{obj.asignacion_id}/entregas/{obj.id}/"


class EntregaDetalleSerializer(serializers.ModelSerializer):
    """Serializador completo de una entrega."""
    estudiante = UsuarioResumenSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    porcentaje_obtenido = serializers.SerializerMethodField()

    class Meta:
        model = Entrega
        fields = (
            'id', 'asignacion', 'estudiante', 'contenido', 'estado',
            'estado_display', 'calificacion', 'porcentaje_obtenido',
            'retroalimentacion', 'fecha_entrega', 'fecha_calificacion',
        )
        read_only_fields = fields

    def get_porcentaje_obtenido(self, obj):
        """
        Calcula el porcentaje obtenido sobre el valor maximo de la asignacion.
        Ej: si la asignacion vale 50 puntos y obtuvo 40, devuelve 80.0 (%).
        """
        if obj.calificacion is None:
            return None
        valor_maximo = obj.asignacion.valor_maximo
        if valor_maximo == 0:
            return 0.0
        return round(float(obj.calificacion / valor_maximo * 100), 2)


class EntregaCrearSerializer(serializers.ModelSerializer):
    """
    Serializador para que un estudiante entregue un trabajo.

    Valida:
    - La asignacion debe aceptar entregas (no vencida o con entrega tardia permitida).
    - El estudiante no puede entregar dos veces (UniqueConstraint en la BD).
    - El estudiante debe estar inscrito en el curso de la asignacion.
    """

    class Meta:
        model = Entrega
        fields = ('contenido',)

    def validate(self, attrs):
        asignacion = self.context['asignacion']
        estudiante = self.context['request'].user

        # Verificar que la asignacion acepta entregas
        if not asignacion.acepta_entregas:
            raise serializers.ValidationError(
                'La fecha de entrega ha vencido y esta asignacion no permite entregas tardias.'
            )

        # Verificar que el estudiante no haya entregado ya
        if Entrega.objects.filter(asignacion=asignacion, estudiante=estudiante).exists():
            raise serializers.ValidationError(
                'Ya realizaste una entrega para esta asignacion.'
            )

        # Verificar inscripcion activa en el curso
        from apps.inscripciones.models import Inscripcion
        inscrito = Inscripcion.objects.filter(
            curso=asignacion.curso,
            estudiante=estudiante,
            estado=Inscripcion.Estado.ACTIVA,
        ).exists()

        if not inscrito:
            raise serializers.ValidationError(
                'Debes estar inscrito activamente en el curso para entregar trabajos.'
            )

        return attrs

    def create(self, validated_data):
        asignacion = self.context['asignacion']
        estudiante = self.context['request'].user
        return Entrega.objects.create(
            asignacion=asignacion,
            estudiante=estudiante,
            estado=Entrega.Estado.ENVIADA,
            **validated_data,
        )


class CalificarEntregaSerializer(serializers.Serializer):
    """
    Serializador dedicado para que el profesor califique una entrega.
    No es un ModelSerializer porque el proceso de calificacion implica
    logica de negocio que delega al metodo Entrega.calificar().
    """
    calificacion = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        help_text='Nota a asignar. No puede superar el valor maximo de la asignacion.',
    )
    retroalimentacion = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text='Comentarios del profesor sobre la entrega (opcional).',
    )

    def validate_calificacion(self, value):
        """Valida que la nota no supere el valor maximo de la asignacion."""
        entrega = self.context['entrega']
        valor_maximo = entrega.asignacion.valor_maximo
        if value > valor_maximo:
            raise serializers.ValidationError(
                f'La calificacion ({value}) supera el valor maximo '
                f'de la asignacion ({valor_maximo}).'
            )
        return value

    def save(self, **kwargs):
        """Delega la logica de negocio al metodo del modelo Entrega."""
        entrega = self.context['entrega']
        entrega.calificar(
            nota=self.validated_data['calificacion'],
            retroalimentacion=self.validated_data.get('retroalimentacion', ''),
        )
        return entrega
