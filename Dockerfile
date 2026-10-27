FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/app/.runtime/huggingface
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home aegis
COPY aegis ./aegis
COPY data ./data
RUN mkdir -p /app/.runtime && chown -R aegis:aegis /app
USER aegis
EXPOSE 8050
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8050/health')"
CMD ["python", "-m", "uvicorn", "aegis.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8050"]
