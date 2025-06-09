# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Command to run the application using gunicorn (a production-ready WSGI server)
# Assumes your Flask app instance is named 'app' in 'main.py'
# You might need to install gunicorn if it's not in requirements.txt yet
# For now, let's add gunicorn to requirements.txt first, then use it here.
# The subtask should first add gunicorn to requirements.txt, then create the Dockerfile.

# Pre-step: Add gunicorn to requirements.txt
# Read current requirements.txt
# Add 'gunicorn' if not present
# Write back requirements.txt

# Dockerfile content (continued):
CMD ["python", "run_daily_job.py"]
