FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "server.py"]
