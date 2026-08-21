# Procfile
# Heroku / Railway / Render - Comandos de proceso para produccion
#
# web: Servidor principal. Gunicorn con 4 workers y timeout de 120s.
#   -w 4         : 4 workers (regla: 2*CPUs + 1 para CPU-bound)
#   --timeout 120: timeout por request para evitar workers colgados
#   --access-logfile -: envia el access log a stdout (visible en los logs del servidor)
#   --error-logfile -: envia el error log a stderr
#   --log-level warning: nivel de log reducido en produccion
#
# NOTA: DJANGO_ENVIRONMENT=production se debe configurar como variable de
#       entorno en el servidor (Heroku Config Vars, Railway Variables, etc.)
#       junto con todas las variables del .env.example
web: gunicorn -c gunicorn.conf.py config.wsgi:application
