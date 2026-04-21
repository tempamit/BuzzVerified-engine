# Use a lightweight official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file from the worker folder and install them
RUN pip install --no-cache-dir -r requirements.txt
COPY requirements.txt .

# Copy ONLY the python worker code (ignores the Laravel MVC folder)
COPY workers-python/ .

# Run the Sucheta Engine
CMD ["python", "-u", "engine.py"]