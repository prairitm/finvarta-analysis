FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python modules
COPY analysis.py .
COPY analysis_service.py .
COPY config.py .
COPY constants.py .
COPY html_extractor.py .
COPY llm_client.py .
COPY screener_client.py .
COPY prompts/ ./prompts/
COPY tools/ ./tools/
COPY cache/ ./cache/

# Create cache directory with write permissions
RUN mkdir -p /app/cache && chmod 777 /app/cache

EXPOSE 8000

CMD ["uvicorn", "analysis:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300", "--timeout-graceful-shutdown", "30"]

