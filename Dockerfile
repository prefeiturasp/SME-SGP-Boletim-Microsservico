FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libpangoft2-1.0-0 libharfbuzz-subset0 \
    fontconfig fonts-dejavu-core \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md manage.py /app/
COPY config /app/config
COPY apps /app/apps
COPY requirements /app/requirements
COPY scripts /app/scripts

RUN pip install --upgrade pip \
    && pip install -r /app/requirements/base.txt

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

