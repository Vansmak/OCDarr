# Use an official Python runtime as a parent image
FROM python:3.8-slim
# Set the working directory in the container
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . /app
# Install any needed packages specified in requirements.txt
COPY requirements.txt /app/ RUN pip install --no-cache-dir -r requirements.txt
# Make port 5000 available to the world outside this container
EXPOSE 5001
# Define environment variable for log path
ENV LOG_PATH=/app/logs/app.log
# Ensure the log directory exists
RUN mkdir -p /app/logs
# Run webhook_listener.py when the container launches
CMD ["python", "webhook_listener.py"]
