"""
config/exceptions.py

Manejador de excepciones personalizado para la API.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('gestion_academica')


def manejador_de_excepciones(exc, context):
    """Manejador de excepciones global para la API REST."""
    if isinstance(exc, Http404):
        exc = exceptions.NotFound(
            detail='El recurso solicitado no fue encontrado.'
        )
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(
            detail='No tienes permiso para realizar esta accion.'
        )

    respuesta = exception_handler(exc, context)

    if respuesta is not None:
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


def _obtener_codigo_error(exc):
    if hasattr(exc, 'default_code'):
        return exc.default_code
    if hasattr(exc, 'get_codes'):
        codigos = exc.get_codes()
        if isinstance(codigos, str):
            return codigos
    return 'error'


def _obtener_mensaje_principal(data):
    if isinstance(data, dict):
        if 'detail' in data:
            detalle = data['detail']
            return str(detalle) if not isinstance(detalle, list) else str(detalle[0])
        primer_campo = next(iter(data))
        primer_error = data[primer_campo]
        if isinstance(primer_error, list):
            return f"Error de validacion en el campo '{primer_campo}': {primer_error[0]}"
        return str(primer_error)
    if isinstance(data, list) and data:
        return str(data[0])
    return 'Se produjo un error en la solicitud.'


def _obtener_errores_detalle(data, exc):
    if not isinstance(exc, exceptions.ValidationError):
        return None

    if isinstance(data, dict) and 'detail' not in data:
        return {
            campo: [str(e) for e in errores] if isinstance(errores, list) else [str(errores)]
            for campo, errores in data.items()
        }
    return None
