FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Créer un utilisateur non-root pour l'exécution
RUN adduser --disabled-password --gecos "" appuser

# ocrmypdf needs: tesseract + ghostscript + qpdf (and poppler utils often)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    ghostscript \
    qpdf \
    unpaper \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn ocrmypdf

WORKDIR /app
COPY app /app/app

# Transférer la propriété à appuser
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
