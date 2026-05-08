FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

# Start both API and UI
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port 8000 & sleep 3 && streamlit run app.py --server.port 8501 --server.address 0.0.0.0"]