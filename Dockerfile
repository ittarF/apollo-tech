FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV TOOL_MANAGER_URL=http://tool-manager:8000
ENV OLLAMA_BASE_URL=http://ollama:11434
ENV DEFAULT_MODEL=gemma3
ENV ENVIRONMENT=production

# Expose the port
EXPOSE 8080

# Start the application
CMD ["python", "main.py"] 