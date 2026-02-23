FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir requests

WORKDIR /app
COPY app /app/app

CMD ["python", "-m", "app.main"]
