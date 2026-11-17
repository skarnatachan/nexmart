web: gunicorn nexmart.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
celery: celery -A nexmart worker --loglevel=info --concurrency=2
