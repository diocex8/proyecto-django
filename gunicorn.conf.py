"""
gunicorn.conf.py

Configuracion avanzada de Gunicorn para produccion.

Uso:
    gunicorn -c gunicorn.conf.py config.wsgi:application
"""

import multiprocessing
import os

# ===========================================================================
# Workers
# ===========================================================================

# Regla general para aplicaciones no asincronas (sync):
#   workers = (2 * numero_de_cpus) + 1
# Para workers sincronos (gthread o sync) con I/O intensivo se puede aumentar.
workers = multiprocessing.cpu_count() * 2 + 1

# Tipo de worker. 'sync' es el mas simple y adecuado para la mayoria de APIs.
# Para cargas muy altas con I/O intensivo considerar 'gthread' o 'gevent'.
worker_class = 'sync'

# Numero de threads por worker. Solo aplica para worker_class='gthread'.
threads = 2

# ===========================================================================
# Conexiones y timeouts
# ===========================================================================

# Tiempo maximo (segundos) que un worker puede tardar en responder.
# Los workers que superan este tiempo son reiniciados por el master.
timeout = 120

# Tiempo maximo de inactividad de una conexion keep-alive (segundos).
keepalive = 5

# Numero maximo de conexiones pendientes en la cola.
backlog = 2048

# ===========================================================================
# Binding
# ===========================================================================

# La direccion donde escucha Gunicorn. En plataformas PaaS como Heroku,
# el puerto lo asigna la plataforma via la variable $PORT.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# ===========================================================================
# Logging
# ===========================================================================

# Enviar logs a stdout/stderr para que el sistema de logs del servidor los capture.
accesslog = '-'
errorlog = '-'
loglevel = 'warning'

# Formato del access log. Incluye tiempo de respuesta para detectar endpoints lentos.
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sus'

# ===========================================================================
# Seguridad
# ===========================================================================

# Limita el tamano del request line para proteger contra ataques
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# ===========================================================================
# Ciclo de vida del proceso
# ===========================================================================

# Numero maximo de requests que un worker atiende antes de ser reiniciado.
# Ayuda a prevenir memory leaks en aplicaciones de larga duracion.
max_requests = 1000
max_requests_jitter = 100  # Introduce aleatoriedad para evitar reinicios sincronizados


def on_starting(server):
    """Hook ejecutado cuando el master Gunicorn inicia."""
    server.log.info('Gunicorn iniciando. Workers: %s', workers)


def worker_exit(server, worker):
    """Hook ejecutado cuando un worker termina. Util para cerrar conexiones abiertas."""
    server.log.info('Worker %s terminado.', worker.pid)
