# consumer/Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copiamos requirements y los instalamos
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY consumer.py ./

# Exponemos el puerto de métricas (opcional)
EXPOSE 8000

# Comando por defecto
CMD ["python", "consumer.py"]
