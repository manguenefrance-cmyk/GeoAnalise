FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN python -c "import rasterio, numpy, pyproj, scipy; print('Raster dependencies loaded')"
COPY services ./services
COPY contracts ./contracts
COPY db ./db
COPY alembic.ini ./alembic.ini
RUN useradd --create-home --uid 10001 arcambe && mkdir -p /app/data && chown -R arcambe:arcambe /app
USER arcambe
EXPOSE 8000
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
