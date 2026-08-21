#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements/production.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate

# Create initial superuser automatically if none exists
python manage.py crear_superusuario_inicial
