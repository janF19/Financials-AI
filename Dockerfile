# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive 

# Prevents interactive prompts during apt-get install

# Install system dependencies for Google Chrome
# 1. Update and install prerequisites for adding repositories and basic tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    # Clean up apt cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Add Google Chrome's official GPG key
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg

# 3. Add the Google Chrome repository
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# 4. Update package list again and install Google Chrome Stable
# This will also pull in necessary dependencies for Chrome.
RUN apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    # Clean up apt cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for database connectors or image processing)
# RUN apt-get update && apt-get install -y --no-install-recommends package-name

# Copy the requirements file from the host's backend directory
# to /app/requirements.txt in the container
COPY ./backend/requirements.txt /app/requirements.txt

# Install any needed packages specified in /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory from the host
# into /app/backend in the container
COPY ./backend /app/backend

# The .env file will be handled by docker-compose at runtime, so no need to copy it here.

# Expose port 8000 to the outside world (for the backend service)
EXPOSE 8000

# The CMD will be specified in docker-compose.yml to differentiate
# between the API server (uvicorn) and the Celery worker. 