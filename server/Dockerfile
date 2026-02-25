# Build stage - generate requirements.txt from Poetry
FROM python:3.10.12-slim as requirements-stage

# Install Poetry and export plugin
RUN pip install poetry poetry-plugin-export

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry and export requirements
RUN poetry config virtualenvs.create false \
    && poetry export -f requirements.txt --output requirements.txt --without-hashes

# Production stage - use generated requirements.txt
FROM python:3.10.12-slim

WORKDIR /app

# Copy requirements from build stage
COPY --from=requirements-stage requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]