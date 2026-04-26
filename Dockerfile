# Slim Python base image
FROM python:3.11-slim

# buffering
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /lab4

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the library folder
COPY pirlib/ pirlib/

# Copy the pipeline entry point script
COPY run_pipeline.py .

# Create output directory
RUN mkdir -p /lab4/output

# Default command when the container starts
CMD ["python", "run_pipeline.py", "--out", "/lab4/output/results.json", "--device-id", "dev1", "--pin", "17","--verbose"]

