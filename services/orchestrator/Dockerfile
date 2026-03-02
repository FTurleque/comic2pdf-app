FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Créer un utilisateur non-root pour l'exécution
RUN adduser --disabled-password --gecos "" appuser

RUN pip install --no-cache-dir requests

WORKDIR /app
COPY app /app/app

# Transférer la propriété à appuser
RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "app.main"]
