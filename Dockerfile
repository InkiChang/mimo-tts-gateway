FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir \
    "fastapi>=0.110" \
    "uvicorn>=0.30" \
    "httpx>=0.27" \
    "aiofiles>=24.0" \
    "jinja2>=3.1" \
    "python-multipart>=0.0.12" \
    "itsdangerous>=2.2" \
    "pydantic>=2.0" \
    "pydantic-settings>=2.0"

COPY backend/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
