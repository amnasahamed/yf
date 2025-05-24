FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies with more verbose output and ignore errors
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    (echo "Failed with exact versions, trying with looser constraints" && \
    sed -i 's/>=[0-9.]*/<999.0.0/g' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt)

# Install yfinance separately in case it's not in requirements
RUN pip install --no-cache-dir yfinance

# Copy application files
COPY . .

# Create log directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]