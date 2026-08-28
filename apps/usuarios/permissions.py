"""
Permisos personalizados del sistema de usuarios.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class EsProfesor(BasePermission):
    """
    Permite acceso a usuarios con rol 'profesor' o 'administrador'.
    """
    message = 'Solo los profesores o administradores pueden realizar esta accion.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.es_profesor or request.user.es_administrador)
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
    - Escritura (POST, PUT, PATCH, DELETE) a profesores o administradores.
    """
    message = 'Solo los profesores o administradores pueden modificar este recurso.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.es_profesor or request.user.es_administrador


class EsPropietarioDelCurso(BasePermission):
    """
    Permiso a nivel de objeto: el profesor propietario o un administrador
    puede modificarlo o eliminarlo.
    """
    message = 'Solo el profesor propietario del curso o un administrador puede realizar esta accion.'

    def has_object_permission(self, request, view, obj):
        if request.user.es_administrador:
            return True
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
    - Un estudiante solo puede gestionar sus propias inscripciones (ver o retirarse).
    - Los profesores pueden ver, calificar y modificar/retirar inscripciones de sus cursos.
    - Los administradores tienen acceso total.
    """
    message = 'No tienes permiso para gestionar esta inscripcion.'

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.es_administrador:
            return True

        if user.es_estudiante:
            if request.method in ('PUT', 'PATCH'):
                return False  # Los estudiantes no pueden alterar estados ni notas directamente
            return obj.estudiante == user

        if user.es_profesor:
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
