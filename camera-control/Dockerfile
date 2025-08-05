# Use a lightweight Python image
FROM python:slim

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY dl-camera-control.py .

# Set python in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Command to run the app
CMD ["python", "dl-camera-control.py"]
