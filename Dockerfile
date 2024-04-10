# Use an official Python runtime as a parent image
FROM python:3.8-slim

# If requests or xml parsing requires system libraries, install them
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables
ENV SERVER_URL=http://example.com \
    SERVER_TOKEN=token_here \
    SONARR_URL=http://sonarr.example.com \
    SONARR_API_KEY=apikey_here \
    WATCHED_PERCENT=90 \
    ALREADY_WATCHED=keep \
    LOG_PATH=/app/logs/app.log

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Ensure the log directory exists
RUN mkdir -p /app/logs

# Run webhook_listener.py when the container launches
CMD ["python", "webhook_listener.py"]
