#!/bin/sh
# Inicia a API Python em background (somente local)
echo "🚀 Iniciando DocOps API Server..."
python3 -u /app/api/server.py &

# Inicia o Nginx em foreground (mantendo o contêiner vivo)
echo "🛡️ Iniciando Nginx Web Server na porta 8000..."
exec nginx -g "daemon off;"
