FROM python:3.12.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# Exact versions that passed the test suite (requirements.txt keeps the ranges).
COPY backend/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock \
 && useradd --uid 10001 --create-home app \
 && mkdir -p /app/data && chown app:app /app/data
COPY backend/ .
COPY knowledge/ /app/knowledge/
COPY dist/catalog.json /app/catalog.json
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
