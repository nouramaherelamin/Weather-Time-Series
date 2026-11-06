FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY django_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY django_app/ ./
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
ENV DJANGO_DEBUG=0 DJANGO_HTTPS=0
EXPOSE 8000
CMD ["sh", "-c", "gunicorn weather_site.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 60"]
