FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY xaiforge ./xaiforge

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "xaiforge", "serve", "--host", "0.0.0.0", "--port", "8000"]
