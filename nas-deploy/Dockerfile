FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pil_api.py .
EXPOSE 8420
CMD ["uvicorn", "pil_api:app", "--host", "0.0.0.0", "--port", "8420"]
