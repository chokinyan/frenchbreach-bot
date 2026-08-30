# --- Base image -------------------------------------------------------
FROM python:3.13-slim


ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Paris

WORKDIR /app


RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential tzdata gosu \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/


RUN mkdir -p /app/src/json


RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app


COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "src/main.py"]