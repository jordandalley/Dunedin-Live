# Use a lightweight Python image
FROM python:slim

# Install ffmpeg and any other system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY build/timelapse-stitcher.py .

# Set python in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Command to run the app
CMD ["python", "timelapse-stitcher.py"]
