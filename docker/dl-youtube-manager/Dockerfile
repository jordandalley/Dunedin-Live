# Use a lightweight Python image
FROM python:slim

# Copy requirements and install
COPY build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY build/youtube-manager.py .

# Set python in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Command to run the app
CMD ["python", "youtube-manager.py"]
