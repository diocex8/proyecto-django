"""
apps/usuarios/serializers.py

Serializadores del dominio de usuarios.

Patron aplicado: Serializadores separados para lectura y escritura.
    - Lectura: Serializadores anidados y con campos calculados (SerializerMethodField).
      Son ricos en informacion pero de solo salida.
    - Escritura: Serializadores planos que validan entrada y aplican logica de negocio.
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

from .models import Usuario

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
        Sobreescribimos para usar email como campo de autenticacion.
        AbstractUser usa 'username' por defecto, pero configuramos
        USERNAME_FIELD = 'email' en el modelo.
        """
        data = super().validate(attrs)
        # Agregar informacion del usuario a la respuesta del token
        data['usuario'] = {
            'id': self.user.pk,
            'email': self.user.email,
            'nombre_completo': self.user.get_full_name(),
            'rol': self.user.rol,
        }
        return data


# ===========================================================================
# Serializers de lectura
# ===========================================================================

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


# ===========================================================================
# Serializadores de ESCRITURA
# ===========================================================================

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro de nuevos usuarios.

    Implementa:
    - Validacion de confirmacion de contrasena.
    - Delegacion al validador de contrasenas de Django (politicas de seguridad).
    - Validacion de unicidad de email a nivel de serializador (ademas del constraint de BD).
    """

    password = serializers.CharField(
        write_only=True,
        min_length=10,
        style={'input_type': 'password'},
        help_text='Minimo 10 caracteres. No puede ser una contrasena comun.',
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
            'rol', 'password', 'password_confirmacion',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        """Validacion a nivel de campo: email en minusculas y unicidad."""
        email_normalizado = value.lower().strip()
        if Usuario.objects.filter(email=email_normalizado).exists():
            raise serializers.ValidationError(
                'Ya existe un usuario registrado con este correo electronico.'
            )
        return email_normalizado

    def validate_rol(self, value):
        """Solo se permite registrarse como Profesor o Estudiante, no como Administrador."""
        roles_permitidos = [Usuario.Rol.PROFESOR, Usuario.Rol.ESTUDIANTE]
        if value not in roles_permitidos:
            raise serializers.ValidationError(
                'El rol de administrador no puede asignarse durante el registro.'
            )
        return value

    def validate(self, attrs):
        """
        Validacion a nivel de objeto: se ejecuta DESPUES de todas las
        validaciones a nivel de campo. Ideal para validaciones que
        involucran multiples campos.
        """
        password = attrs.get('password')
        password_confirmacion = attrs.pop('password_confirmacion', None)

        if password != password_confirmacion:
            raise serializers.ValidationError({
                'password_confirmacion': 'Las contrasenas no coinciden.'
            })

        # Delegar al sistema de validacion de contrasenas de Django
        # Esto aplica todas las politicas configuradas en AUTH_PASSWORD_VALIDATORS
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return attrs

    def create(self, validated_data):
        """
        Usa create_user() en lugar de create() para que Django hashee
        la contrasena correctamente. Nunca almacenar contrasenas en texto plano.
        """
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        logger.info(
            'Nuevo usuario registrado. Email: %s, Rol: %s',
            usuario.email, usuario.rol
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

    Decision: Se separa en su propio serializador (no en ModelSerializer)
    porque el proceso de cambio de contrasena requiere:
    1. Verificar la contrasena actual.
    2. Validar la nueva contrasena con las politicas de seguridad.
    3. Hashear y guardar.

    Este flujo no encaja limpiamente en un ModelSerializer.
    """
    password_actual = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )
    password_nuevo = serializers.CharField(
        write_only=True,
        min_length=10,
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
