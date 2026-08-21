"""
apps/usuarios/permissions.py

Permisos personalizados del sistema de usuarios.

Decision de arquitectura:
    DRF separa autenticacion (quien eres) de autorizacion (que puedes hacer).
    Los permisos aqui implementados actuan a dos niveles:

    1. Nivel de vista (has_permission): se evalua para toda la peticion
       antes de procesar nada. Ej: "solo profesores pueden acceder a este endpoint".

    2. Nivel de objeto (has_object_permission): se evalua para un objeto
       especifico. Ej: "solo el propietario del curso puede eliminarlo".

    Los permisos se combinan con el operador AND en las vistas usando listas:
        permission_classes = [IsAuthenticated, EsProfesor]

    Para combinar con OR se usa el operador | de DRF:
        permission_classes = [EsProfesor | EsAdministrador]
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class EsProfesor(BasePermission):
    """
    Permite acceso solo a usuarios con rol 'profesor'.
    El mensaje se muestra en la respuesta de error estandarizada.
    """
    message = 'Solo los profesores pueden realizar esta accion.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.es_profesor
        )


class EsEstudiante(BasePermission):
    """Permite acceso solo a usuarios con rol 'estudiante'."""
    message = 'Solo los estudiantes pueden realizar esta accion.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.es_estudiante
        )


class EsProfesorOSoloLectura(BasePermission):
    """
    Permite:
    - Lectura (GET, HEAD, OPTIONS) a cualquier usuario autenticado.
    - Escritura (POST, PUT, PATCH, DELETE) solo a profesores.

    Util para endpoints donde los estudiantes pueden ver pero no modificar.
    """
    message = 'Solo los profesores pueden modificar este recurso.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.es_profesor


class EsPropietarioDelCurso(BasePermission):
    """
    Permiso a nivel de objeto: solo el profesor que creo el curso
    puede modificarlo o eliminarlo.

    Se combina con EsProfesor en las vistas:
        permission_classes = [IsAuthenticated, EsProfesor, EsPropietarioDelCurso]
    """
    message = 'Solo el profesor propietario del curso puede realizar esta accion.'

    def has_object_permission(self, request, view, obj):
        # Acceso de lectura permitido al propietario y a los administradores
        if request.method in SAFE_METHODS:
            return True
        return obj.profesor == request.user


class EsEstudianteInscritoOProfesorPropietario(BasePermission):
    """
    Para ver el detalle de un curso:
    - El estudiante debe estar inscrito y activo en el curso.
    - El profesor debe ser el propietario del curso.
    - Los administradores siempre tienen acceso.
    """
    message = 'No tienes acceso a este curso. Debes estar inscrito o ser el profesor responsable.'

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.es_administrador:
            return True

        if user.es_profesor:
            return obj.profesor == user

        if user.es_estudiante:
            # Verificar inscripcion activa evitando import circular
            from apps.inscripciones.models import Inscripcion
            return obj.inscripciones.filter(
                estudiante=user,
                estado=Inscripcion.Estado.ACTIVA
            ).exists()

        return False


class EsPropietarioDeLaInscripcion(BasePermission):
    """
    Un estudiante solo puede gestionar sus propias inscripciones.
    Los profesores tienen acceso de lectura a inscripciones de sus cursos.
    """
    message = 'No tienes permiso para gestionar esta inscripcion.'

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.es_administrador:
            return True

        if user.es_estudiante:
            return obj.estudiante == user

        if user.es_profesor and request.method in SAFE_METHODS:
            # El profesor puede leer inscripciones de sus cursos
            return obj.curso.profesor == user

        return False


class EsPropietarioDeLaEntrega(BasePermission):
    """
    - El estudiante solo puede ver y editar sus propias entregas.
    - El profesor del curso puede leer y calificar todas las entregas de su curso.
    """
    message = 'No tienes permiso para acceder a esta entrega.'

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.es_administrador:
            return True

        if user.es_estudiante:
            return obj.estudiante == user

        if user.es_profesor:
            return obj.asignacion.curso.profesor == user

        return False
