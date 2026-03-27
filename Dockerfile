FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create data directory
RUN mkdir -p /app/data_0

# Expose port
EXPOSE 5001

# Set environment
ENV FLASK_APP=app.py

CMD ["python", "app.py"]