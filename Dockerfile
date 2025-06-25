# Use official Python image
FROM python:3.12

# Set working directory
WORKDIR /app

# Copy dependencies file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port your app runs on
EXPOSE 8000

# Run the app with Uvicorn
CMD ["bash", "-c", "sleep 25 && python run_webapp.py --host 0.0.0.0 --port 8000"]
