#!/bin/sh
set -eu

# Run migrations before starting the API.
python manage.py migrate --noinput

exec python manage.py runserver 0.0.0.0:"${PORT:-8000}"

