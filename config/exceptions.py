"""
config/exceptions.py

Manejador de excepciones personalizado para la API.

Problema que resuelve:
    Por defecto, DRF devuelve formatos de error inconsistentes:
    - Errores de validacion: {"campo": ["mensaje"]}
    - Errores de autenticacion: {"detail": "..."}
    - Errores 500: pagina HTML de Django (inaceptable en una API)

Solucion:
    Un manejador unico que garantiza que TODA respuesta de error de la API
    sea un JSON con la misma estructura, independientemente del tipo de error.

Estructura estandar de respuesta de error:
    {
        "exito": false,
        "codigo": "nombre_del_error",
        "mensaje": "Descripcion legible del error.",
        "errores": { ... }  // Solo en errores de validacion
    }
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('gestion_academica')


def manejador_de_excepciones(exc, context):
    """
    Manejador de excepciones global para toda la API REST.

    Intercepta tanto excepciones de DRF como excepciones nativas de Django
    (Http404, PermissionDenied) y las transforma a un formato JSON unificado.
    Los errores 500 no capturados se registran en el sistema de logging.
    """

    # Convertir excepciones nativas de Django a equivalentes de DRF
    if isinstance(exc, Http404):
        exc = exceptions.NotFound(
            detail='El recurso solicitado no fue encontrado.'
        )
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(
            detail='No tienes permiso para realizar esta accion.'
        )

    # Delegar al manejador estandar de DRF para que prepare la respuesta base
    respuesta = exception_handler(exc, context)

    if respuesta is not None:
        # La excepcion es de tipo DRF (4xx): estandarizar el formato
        codigo_error = _obtener_codigo_error(exc)
        mensaje = _obtener_mensaje_principal(respuesta.data)
        errores = _obtener_errores_detalle(respuesta.data, exc)

        datos_respuesta = {
            'exito': False,
            'codigo': codigo_error,
            'mensaje': mensaje,
        }

        if errores:
            datos_respuesta['errores'] = errores

        respuesta.data = datos_respuesta
        return respuesta

    # Si respuesta es None, es un error 500 no manejado.
    # Se registra el error y se devuelve una respuesta JSON controlada
    # en lugar de la pagina de error HTML de Django.
    vista = context.get('view', None)
    logger.error(
        'Error interno no controlado en la API.',
        exc_info=exc,
        extra={
            'vista': vista.__class__.__name__ if vista else 'Desconocida',
        }
    )

    return Response(
        {
            'exito': False,
            'codigo': 'error_interno_del_servidor',
            'mensaje': (
                'Ocurrio un error interno en el servidor. '
                'El equipo tecnico ha sido notificado.'
            ),
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ===========================================================================
# Funciones auxiliares privadas
# ===========================================================================

def _obtener_codigo_error(exc):
    """Extrae el codigo de error de la excepcion para uso programatico."""
    if hasattr(exc, 'default_code'):
        return exc.default_code
    if hasattr(exc, 'get_codes'):
        codigos = exc.get_codes()
        if isinstance(codigos, str):
            return codigos
    return 'error'


def _obtener_mensaje_principal(data):
    """
    Extrae el mensaje principal de la respuesta de error.
    Maneja tanto el formato {'detail': '...'} como listas de errores.
    """
    if isinstance(data, dict):
        if 'detail' in data:
            detalle = data['detail']
            return str(detalle) if not isinstance(detalle, list) else str(detalle[0])
        # En errores de validacion, construir un mensaje general
        primer_campo = next(iter(data))
        primer_error = data[primer_campo]
        if isinstance(primer_error, list):
            return f"Error de validacion en el campo '{primer_campo}': {primer_error[0]}"
        return str(primer_error)
    if isinstance(data, list) and data:
        return str(data[0])
    return 'Se produjo un error en la solicitud.'


def _obtener_errores_detalle(data, exc):
    """
    Para errores de validacion (422), devuelve el mapa completo de errores
    por campo. Para otros errores (401, 403, 404), no aplica.
    """
    if not isinstance(exc, exceptions.ValidationError):
        return None

    if isinstance(data, dict) and 'detail' not in data:
        # Es un error de validacion con campos: devolver el mapa completo
        return {
            campo: [str(e) for e in errores] if isinstance(errores, list) else [str(errores)]
            for campo, errores in data.items()
        }
    return None
