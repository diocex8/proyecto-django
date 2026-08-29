set -o errexit

pip install -r requirements/production.txt

python manage.py collectstatic --no-input

python manage.py migrate

python manage.py crear_superusuario_inicial
