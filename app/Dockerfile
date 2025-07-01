# Usar una imagen base de Python oficial y ligera
FROM python:3.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos primero para aprovechar el cache de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# Exponer el puerto en el que Gunicorn se ejecutará
EXPOSE 8000

# Comando para ejecutar la aplicación usando Gunicorn con 2 workers
# Esto es más robusto que `flask run` para producción
CMD ["gunicorn", "--workers", "2", "--timeout", "120", "--bind", "0.0.0.0:8000", "app:app"]