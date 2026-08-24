FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml README.md constraints.txt ./
COPY app ./app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -c constraints.txt . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin vouch

USER vouch

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "from urllib.request import urlopen; response = urlopen('http://127.0.0.1:8000/healthz', timeout=2); raise SystemExit(0 if response.status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
