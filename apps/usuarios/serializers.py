"""
Serializadores del dominio de usuarios.

Patron aplicado: Serializadores separados para lectura y escritura.
    - Lectura: Serializadores anidados y con campos calculados (SerializerMethodField).
      Son ricos en informacion pero de solo salida.
    - Escritura: Serializadores planos que validan entrada y aplican funciones.
      Son simples, rapidos y con validaciones estrictas.

    Esta separacion evita el anti-patron de tener un unico serializador
    que intenta servir para ambos propositos, lo que genera complejidad
    innecesaria en las validaciones y los campos.
"""

import logging

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario, SolicitudProfesor

logger = logging.getLogger('gestion_academica')


class TokenPersonalizadoObtainSerializer(TokenObtainPairSerializer):
    """
    Serializador JWT personalizado que embebe informacion del usuario
    en el payload del token para evitar consultas adicionales a la BD.

    El cliente JWT puede decodificar el payload (sin verificar la firma)
    para leer el rol, nombre y email del usuario sin hacer peticiones extras.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims adicionales embebidos en el JWT
        token['rol'] = user.rol
        token['nombre_completo'] = user.get_full_name()
        token['email'] = user.email
        return token

    def validate(self, attrs):
        """
        Sobreescribimos para usar email como campo de autenticacion y
        proporcionar mensajes especificos si la cuenta de profesor esta
        pendiente de aprobacion o fue rechazada.
        """
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password')

        # Verificacion previa del estado del usuario para mensajes claros
        usuario = Usuario.objects.filter(email=email).first()
        if usuario and usuario.check_password(password) and not usuario.is_active:
            if usuario.es_profesor and hasattr(usuario, 'solicitud_profesor'):
                solicitud = usuario.solicitud_profesor
                if solicitud.estado == SolicitudProfesor.Estado.PENDIENTE:
                    raise serializers.ValidationError({
                        'detail': 'Tu solicitud de profesor esta pendiente de aprobacion por un administrador.'
                    })
                elif solicitud.estado == SolicitudProfesor.Estado.RECHAZADA:
                    raise serializers.ValidationError({
                        'detail': 'Tu solicitud de profesor fue rechazada. No puedes iniciar sesion.'
                    })
            raise serializers.ValidationError({
                'detail': 'Esta cuenta se encuentra inactiva. Contacta al administrador.'
            })

        data = super().validate(attrs)
        # Agregar informacion del usuario a la respuesta del token
        data['usuario'] = {
            'id': self.user.pk,
            'email': self.user.email,
            'nombre_completo': self.user.get_full_name(),
            'rol': self.user.rol,
        }
        return data

class UsuarioResumenSerializer(serializers.ModelSerializer):
    """
    Serializador compacto para referencias a usuarios embebidos en otros recursos.
    Ej: cuando se devuelve un Curso, el campo 'profesor' usa este serializador.
    """
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ('id', 'email', 'nombre_completo', 'rol')
        read_only_fields = fields

    def get_nombre_completo(self, obj):
        return obj.get_full_name()


class UsuarioDetalleSerializer(serializers.ModelSerializer):
    """
    Serializador completo para el perfil propio del usuario autenticado.
    Incluye campos calculados y estadisticas.
    """
    nombre_completo = serializers.SerializerMethodField()
    total_cursos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'nombre_completo', 'rol', 'is_active',
            'fecha_registro', 'ultima_actualizacion', 'total_cursos',
        )
        read_only_fields = fields

    def get_nombre_completo(self, obj):
        return obj.get_full_name()

    def get_total_cursos(self, obj):
        """
        Campo calculado: total de cursos del usuario segun su rol.

        OPTIMIZACION: Este metodo hace una consulta a la BD por cada usuario
        serializado. Para evitar N+1 en listados, se debe usar annotate() en
        el queryset de la vista y pasar el valor anotado desde ahi.

        La vista inyecta el valor via contexto cuando esta disponible:
            def get_queryset(self):
                return Usuario.objects.annotate(total_cursos=Count(...))
        """
        if obj.es_profesor:
            # Si el queryset ya tiene el valor anotado, lo usa directamente
            if hasattr(obj, 'total_cursos_anotado'):
                return obj.total_cursos_anotado
            return obj.cursos_como_profesor.count()
        elif obj.es_estudiante:
            if hasattr(obj, 'total_inscripciones_anotado'):
                return obj.total_inscripciones_anotado
            return obj.inscripciones_como_estudiante.filter(
                estado='activa'
            ).count()
        return 0

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro de nuevos usuarios.

    Reglas:
    - Solo permite roles 'estudiante' o 'profesor'.
    - Si el rol es 'profesor', la cuenta se crea inactiva y genera una SolicitudProfesor pendiente.
    - Si una solicitud previa fue rechazada, bloquea el registro durante 2 horas (cooldown).
    - Valida confirmacion de contrasena y fortaleza.
    """

    email = serializers.EmailField(
        required=True,
        help_text='Direccion de correo electronico.',
    )
    username = serializers.CharField(
        required=True,
        help_text='Nombre de usuario.',
    )
    rol = serializers.ChoiceField(
        choices=[
            (Usuario.Rol.ESTUDIANTE, 'Estudiante'),
            (Usuario.Rol.PROFESOR, 'Profesor'),
        ],
        default=Usuario.Rol.ESTUDIANTE,
        help_text='Rol para el registro: solo se permite estudiante o profesor.',
    )
    first_name = serializers.CharField(
        required=True,
        help_text='Nombre(s) del usuario.'
    )
    last_name = serializers.CharField(
        required=True,
        help_text='Apellido(s) del usuario.'
    )
    password = serializers.CharField(
        write_only=True,
        min_length=5,
        style={'input_type': 'password'},
        help_text='Minimo 5 caracteres.',
    )
    password_confirmacion = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='Debe coincidir exactamente con el campo "password".',
    )

    class Meta:
        model = Usuario
        fields = (
            'email', 'username', 'first_name', 'last_name',
            'rol', 'password', 'password_confirmacion'
        )
        extra_kwargs = {
            'email': {'validators': []},
            'username': {'validators': []},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        """
        Validacion de email:
        - Normalizacion a minusculas.
        - Verificacion de cooldown de 2 horas si hubo una solicitud rechazada previa.
        - Verificacion de solicitudes pendientes o usuarios activos existentes.
        """
        email_normalizado = value.lower().strip()

        # Comprobar solicitudes previas asociadas a este correo
        solicitud_previa = SolicitudProfesor.objects.filter(
            email=email_normalizado
        ).order_by('-fecha_solicitud').first()

        if solicitud_previa:
            if solicitud_previa.esta_en_cooldown():
                minutos_restantes = solicitud_previa.tiempo_restante_cooldown()
                raise serializers.ValidationError(
                    f'Tu solicitud previa como profesor fue rechazada. '
                    f'Debes esperar 2 horas antes de volver a registrarte. '
                    f'Tiempo de espera restante: {minutos_restantes} minuto(s).'
                )
            elif solicitud_previa.estado == SolicitudProfesor.Estado.PENDIENTE:
                raise serializers.ValidationError(
                    'Ya existe una solicitud de profesor pendiente de aprobacion para este correo electronico.'
                )

        # Comprobar si existe un usuario activo
        if Usuario.objects.filter(email=email_normalizado, is_active=True).exists():
            raise serializers.ValidationError(
                'Ya existe un usuario registrado con este correo electronico.'
            )

        return email_normalizado

    def validate_username(self, value):
        """Valida que el nombre de usuario no pertenezca a una cuenta activa."""
        username_limpio = value.strip()
        if Usuario.objects.filter(username=username_limpio, is_active=True).exists():
            raise serializers.ValidationError(
                'Ya existe un usuario con este nombre de usuario.'
            )
        return username_limpio

    def validate_rol(self, value):
        """Solo se permite registrarse como Profesor o Estudiante."""
        roles_permitidos = [Usuario.Rol.PROFESOR, Usuario.Rol.ESTUDIANTE]
        if value not in roles_permitidos:
            raise serializers.ValidationError(
                'Solo se permite el registro con rol estudiante o profesor.'
            )
        return value

    def validate(self, attrs):
        """
        Validacion a nivel de objeto: coincidencia de contrasenas y validadores de Django.
        """
        password = attrs.get('password')
        password_confirmacion = attrs.pop('password_confirmacion', None)

        if password != password_confirmacion:
            raise serializers.ValidationError({
                'password_confirmacion': 'Las contrasenas no coinciden.'
            })

        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return attrs

    def create(self, validated_data):
        """
        Crea el usuario. Si es profesor, se crea inactivo (is_active=False)
        y se registra su SolicitudProfesor. Si es estudiante, se activa de inmediato.
        """
        password = validated_data.pop('password')
        email = validated_data.get('email')
        rol = validated_data.get('rol')

        # Si habia un registro anterior inactivo con cooldown ya expirado, limpiarlo
        Usuario.objects.filter(email=email, is_active=False).delete()

        usuario = Usuario(**validated_data)
        usuario.set_password(password)

        if rol == Usuario.Rol.PROFESOR:
            usuario.is_active = False
            usuario.save()
            SolicitudProfesor.objects.create(
                usuario=usuario,
                email=usuario.email,
                estado=SolicitudProfesor.Estado.PENDIENTE,
            )
            logger.info(
                'Nueva solicitud de profesor registrada. Email: %s (cuenta inactiva)',
                usuario.email
            )
        else:
            usuario.is_active = True
            usuario.save()
            logger.info(
                'Nuevo estudiante registrado. Email: %s (cuenta activa)',
                usuario.email
            )

        return usuario


class ActualizarPerfilSerializer(serializers.ModelSerializer):
    """
    Permite al usuario actualizar solo sus campos de perfil publicos.
    No permite cambiar el email, rol ni la contrasena desde aqui
    (la contrasena tiene su propio endpoint dedicado por seguridad).
    """

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name')

    def validate_username(self, value):
        """Valida que el nuevo username no este en uso por otro usuario."""
        usuario_actual = self.instance
        if (
            Usuario.objects.filter(username=value)
            .exclude(pk=usuario_actual.pk)
            .exists()
        ):
            raise serializers.ValidationError(
                'Este nombre de usuario ya esta en uso.'
            )
        return value


class CambiarPasswordSerializer(serializers.Serializer):
    """
    Serializador dedicado para el cambio de contrasena.
    """
    password_actual = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )
    password_nuevo = serializers.CharField(
        write_only=True,
        min_length=5,
        style={'input_type': 'password'},
    )
    password_nuevo_confirmacion = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    def validate_password_actual(self, value):
        """Verifica que la contrasena actual sea correcta antes de permitir el cambio."""
        usuario = self.context['request'].user
        if not usuario.check_password(value):
            raise serializers.ValidationError('La contrasena actual es incorrecta.')
        return value

    def validate(self, attrs):
        nuevo = attrs.get('password_nuevo')
        confirmacion = attrs.get('password_nuevo_confirmacion')

        if nuevo != confirmacion:
            raise serializers.ValidationError({
                'password_nuevo_confirmacion': 'Las contrasenas nuevas no coinciden.'
            })

        try:
            validate_password(nuevo, user=self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password_nuevo': list(e.messages)})

        return attrs

    def save(self, **kwargs):
        usuario = self.context['request'].user
        usuario.set_password(self.validated_data['password_nuevo'])
        usuario.save(update_fields=['password'])
        logger.info('Contrasena cambiada para el usuario ID: %s', usuario.pk)
        return usuario


class SolicitudProfesorListaSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='usuario.get_full_name', read_only=True)
    username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = SolicitudProfesor
        fields = (
            'id', 'email', 'username', 'nombre_completo',
            'estado', 'fecha_solicitud', 'fecha_resolucion', 'motivo_rechazo'
        )
        read_only_fields = fields


class RechazarSolicitudSerializer(serializers.Serializer):
    motivo = serializers.CharField(
        required=True,
        help_text='Motivo por el cual se rechaza la solicitud.',
        style={'base_template': 'textarea.html'}
    )
