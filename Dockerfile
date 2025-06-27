# Use the official Python image with Playwright dependencies
FROM mcr.microsoft.com/playwright/python:v1.44.0-focal

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Set environment variables (adjust as needed)
ENV PYTHONUNBUFFERED=1

# Expose port if running an API (adjust as needed)
EXPOSE 8000

# Default command (adjust as needed)
CMD ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
