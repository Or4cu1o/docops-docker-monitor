FROM python:3.11-alpine

LABEL maintainer="DocOps"
LABEL description="Monitor DevOps Bare-Metal Inviolável"
LABEL org.opencontainers.image.source="https://hub.docker.com/r/or4cu1o/docops"

# Instala o Web Server (Nginx)
RUN apk add --no-cache nginx

# Define o diretório principal
WORKDIR /app

# Copia e aplica as configurações de Infraestrutura
COPY .docker/nginx.conf /etc/nginx/http.d/default.conf
COPY .docker/entrypoint.sh /app/entrypoint.sh

# Copia os módulos da aplicação
COPY api/ ./api/
COPY public/ ./public/
COPY web/ ./web/

# Expõe estritamente a porta do Nginx
EXPOSE 8000

# Executa o orquestrador
CMD ["/app/entrypoint.sh"]