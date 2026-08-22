"""
config/pagination.py

Clases de paginacion personalizadas del proyecto.
"""

from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response


class PaginacionEstandar(PageNumberPagination):
    """
    Paginacion por numero de pagina para listados generales.

    El cliente controla el tamano de pagina hasta un maximo de 100 registros
    para evitar consultas masivas que saturen la base de datos.
    """
    page_size = 20
    page_size_query_param = 'tam_pagina'
    max_page_size = 100
    page_query_param = 'pagina'

    def get_paginated_response(self, data):
        """
        Sobreescribimos para estandarizar la estructura de la respuesta paginada.
        Todos los endpoints de lista devuelven la misma forma de respuesta.
        """
        return Response({
            'paginacion': {
                'total_registros': self.page.paginator.count,
                'total_paginas': self.page.paginator.num_pages,
                'pagina_actual': self.page.number,
                'siguiente': self.get_next_link(),
                'anterior': self.get_previous_link(),
            },
            'resultados': data,
        })

    def get_paginated_response_schema(self, schema):
        """Esquema para la documentacion automatica de la API."""
        return {
            'type': 'object',
            'properties': {
                'paginacion': {
                    'type': 'object',
                    'properties': {
                        'total_registros': {'type': 'integer'},
                        'total_paginas': {'type': 'integer'},
                        'pagina_actual': {'type': 'integer'},
                        'siguiente': {'type': 'string', 'nullable': True},
                        'anterior': {'type': 'string', 'nullable': True},
                    }
                },
                'resultados': schema,
            }
        }


class PaginacionInscripciones(LimitOffsetPagination):
    """
    Paginacion por limit/offset para el endpoint de inscripciones.

    Se usa LimitOffsetPagination aqui porque permite saltar directamente
    a cualquier posicion del conjunto de datos, util para exportaciones
    parciales y dashboards con scroll infinito.
    """
    default_limit = 25
    max_limit = 200
    limit_query_param = 'limite'
    offset_query_param = 'desplazamiento'

    def get_paginated_response(self, data):
        return Response({
            'paginacion': {
                'total_registros': self.count,
                'limite': self.limit,
                'desplazamiento': self.offset,
                'siguiente': self.get_next_link(),
                'anterior': self.get_previous_link(),
            },
            'resultados': data,
        })
