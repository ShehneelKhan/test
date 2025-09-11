# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (Xvfb for virtual display, plus required libs for screenshots & tesseract if needed later)
RUN apt-get update && apt-get install -y \
    xvfb \
    libx11-6 \
    libxtst6 \
    libxrender1 \
    libxi6 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy dependency files first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose Render port
EXPOSE 10000

# Run the app under Xvfb so screenshots work
CMD ["xvfb-run", "-a", "uvicorn", "backend.api_server:app", "--host", "0.0.0.0", "--port", "10000"]
