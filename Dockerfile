# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Update system packages and install dependencies
# Install necessary system libraries for Python packages if needed
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libxml2-dev \
       libxslt-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt /app/

# Install Python dependencies listed in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the static directory first
COPY static /app/static

# Copy the rest of the application's code to the container
COPY . /app/

# Define environment variables for runtime
ENV SONARR_URL=http://sonarr.example.com \
    SONARR_API_KEY=apikey_here \
    LOG_PATH=/app/logs/app.log

# Create a directory for logs
RUN mkdir -p /app/logs

# Expose port 5001 to allow communication to/from the server
EXPOSE 5001

# Use Gunicorn to serve the application
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5001", "webhook_listener:app"]