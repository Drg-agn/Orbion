FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Generate sample data if not present on container start
RUN python data/sample_data.py || true

EXPOSE 8000

CMD ["python", "run.py"]
