from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.cursos.models import Curso
from apps.cursos.serializers import CursoListaSerializer
from apps.usuarios.serializers import UsuarioResumenSerializer
from apps.inscripciones.models import Inscripcion


class InscripcionListaSerializer(serializers.ModelSerializer):
    """Serializador de lectura con datos anidados de curso y estudiante, incluyendo rendimiento academico."""
    curso = CursoListaSerializer(read_only=True)
    estudiante = UsuarioResumenSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    rendimiento_academico = serializers.SerializerMethodField()
    url_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = (
            'id', 'curso', 'estudiante', 'estado',
            'estado_display', 'nota_final', 'rendimiento_academico',
            'fecha_inscripcion', 'url_detalle',
        )
        read_only_fields = fields

    def get_url_detalle(self, obj):
        return f"/api/v1/inscripciones/{obj.id}/"

    def get_rendimiento_academico(self, obj):
        return obj.calcular_estadisticas_academicas()


class InscripcionDetalleSerializer(serializers.ModelSerializer):
    """Serializador completo de una inscripcion individual."""
    curso = CursoListaSerializer(read_only=True)
    estudiante = UsuarioResumenSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    rendimiento_academico = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = (
            'id', 'curso', 'estudiante', 'estado',
            'estado_display', 'nota_final', 'rendimiento_academico',
            'fecha_inscripcion', 'fecha_actualizacion',
        )
        read_only_fields = (
            'id', 'curso', 'estudiante', 'estado_display',
            'rendimiento_academico', 'fecha_inscripcion', 'fecha_actualizacion',
        )

    def get_rendimiento_academico(self, obj):
        return obj.calcular_estadisticas_academicas()


class InscripcionModificarSerializer(serializers.ModelSerializer):
    """
    Permite a profesores y administradores modificar el estado de una inscripcion.
    La nota final se calcula automaticamente a partir de las asignaciones calificadas.
    """
    class Meta:
        model = Inscripcion
        fields = ('estado',)


class InscripcionCrearSerializer(serializers.ModelSerializer):
    """
    Serializador para inscribir a un estudiante en un curso.
    - Estudiantes y Profesores: solo eligen el curso, la solicitud queda en PENDIENTE.
    - Administradores: pueden inscribir a un estudiante directamente con estado ACTIVA.
    """
    curso_id = serializers.PrimaryKeyRelatedField(
        queryset=Curso.objects.filter(estado=Curso.Estado.PUBLICADO),
        source='curso',
        help_text='Selecciona el curso al que deseas inscribirte.',
    )
    estudiante_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(rol='estudiante'),
        source='estudiante',
        required=False,
        allow_null=True,
        help_text='(Solo Admins) ID del estudiante a inscribir.',
    )

    class Meta:
        model = Inscripcion
        fields = ('curso_id', 'estudiante_id')
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            # Solo los administradores ven el campo estudiante_id
            if not getattr(user, 'es_administrador', False):
                self.fields.pop('estudiante_id', None)
            # Los profesores solo ven sus propios cursos
            if getattr(user, 'es_profesor', False) and not getattr(user, 'es_administrador', False):
                self.fields['curso_id'].queryset = Curso.objects.filter(
                    estado=Curso.Estado.PUBLICADO, profesor=user
                )

    def validate(self, attrs):
        user = self.context['request'].user
        curso = attrs.get('curso')
        estudiante = attrs.get('estudiante')

        # Estudiantes y profesores se inscriben/solicitan a ellos mismos
        if not getattr(user, 'es_administrador', False):
            estudiante = user
            attrs['estudiante'] = user
        else:
            if not estudiante:
                raise serializers.ValidationError({
                    'estudiante_id': 'Como administrador, debes seleccionar el estudiante a inscribir.'
                })

        # Verificar si ya existe una inscripcion previa
        inscripcion_existente = Inscripcion.objects.filter(
            curso=curso,
            estudiante=estudiante,
        ).first()

        if inscripcion_existente:
            if inscripcion_existente.estado == Inscripcion.Estado.ACTIVA:
                raise serializers.ValidationError(
                    f'El estudiante "{estudiante.get_full_name() or estudiante.username}" ya esta inscrito activamente en este curso.'
                )
            elif inscripcion_existente.estado == Inscripcion.Estado.PENDIENTE:
                raise serializers.ValidationError(
                    'Ya existe una solicitud de inscripcion pendiente para este curso. Espera la aprobacion.'
                )
            elif inscripcion_existente.estado in (Inscripcion.Estado.RETIRADA, Inscripcion.Estado.RECHAZADA):
                attrs['inscripcion_reactivada'] = inscripcion_existente
                return attrs

        # Verificar cupos disponibles en el curso
        if curso.cupos_disponibles <= 0:
            raise serializers.ValidationError(
                f'El curso "{curso.nombre}" no tiene cupos disponibles (Capacidad: {curso.capacidad_maxima}).'
            )

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        # Solo el admin puede inscribir directamente con estado ACTIVA
        nuevo_estado = Inscripcion.Estado.ACTIVA if getattr(user, 'es_administrador', False) else Inscripcion.Estado.PENDIENTE

        inscripcion_reactivada = validated_data.pop('inscripcion_reactivada', None)
        if inscripcion_reactivada:
            inscripcion_reactivada.estado = nuevo_estado
            inscripcion_reactivada.save(update_fields=['estado', 'fecha_actualizacion'])
            return inscripcion_reactivada

        validated_data['estado'] = nuevo_estado
        return Inscripcion.objects.create(**validated_data)
