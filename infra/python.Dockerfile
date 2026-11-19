FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY services ./services
COPY contracts ./contracts
COPY db ./db
COPY alembic.ini ./alembic.ini
RUN useradd --create-home --uid 10001 arcambe && mkdir -p /app/data && chown -R arcambe:arcambe /app
USER arcambe
EXPOSE 8000
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
