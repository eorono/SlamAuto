# Usar la imagen oficial de Nginx
FROM nginx:stable-alpine

# Eliminar la configuración por defecto
RUN rm /etc/nginx/conf.d/default.conf

# Copiar nuestro archivo de configuración personalizado
COPY nginx.conf /etc/nginx/conf.d/