FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Ensure SQLite can be written (HF spaces runs as user 1000)
RUN chmod 777 .
RUN chmod 777 logs

# Expose the required Hugging Face port
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "scheduler:app", "--host", "0.0.0.0", "--port", "7860"]
