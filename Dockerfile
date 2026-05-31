
FROM python:3.10-slim

WORKDIR /app
#dependencies install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copying whole code
COPY . .

# running app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
