FROM python:3.11-slim

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY proxy/pyproject.toml proxy/uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY proxy/main.py ./

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
