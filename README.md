# 🐋 DocOps - Docker Monitor for DevOps

[![Build and Publish](https://github.com/or4cu1o/docops-docker-monitor/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/or4cu1o/docops-docker-monitor/actions)
[![Docker Pulls](https://img.shields.io/docker/pulls/or4cu1o/docops.svg)](https://hub.docker.com/r/or4cu1o/docops)
[![Language](https://img.shields.io/badge/Language-Python-blue.svg)](https://www.python.org/)

![DocOps Banner](https://raw.githubusercontent.com/or4cu1o/docops-docker-monitor/main/public/assets/banner.png)

O **DocOps** é um painel de telemetria simples e eficiente para servidores Linux e infraestruturas Docker. Desenvolvido para entregar visibilidade de borda com latência zero, consumo de recursos insignificante e uma arquitetura de segurança inviolável.

---

## 📊 Visualização de Projetos e Métricas

### 🖥️ Dados do Host (VPS/Bare-Metal)

- **Recursos:** Uso real de CPU, RAM e Armazenamento.
- **Performance:** Carga de Disk I/O e Load Average.
- **Rede:** Monitoramento de tráfego (TX/RX) em tempo real com gráfico de tendência.

### 📦 Dados de Containers e Docker

- **Métricas Individuais:** Consumo de CPU, RAM e I/O por container.
- **Status:** Monitoramento de estado (Running/Stopped) e imagens em execução.
- **Agrupamento:** Organização automática por projetos (Docker Compose).

### 🌐 Domínios, Proxies e DNS

- **Proxy Reverso:** Detecção automática de rotas e domínios via **Traefik**, **Nginx** e **Apache**.
- **Rede:** Exposição de portas públicas e mapeamentos internos.
- **Serviços Críticos:** Identificação e monitoramento especializado para **Pi-hole** e serviços de DNS/Infraestrutura.

### 🖼️ Screenshots

![DocOps Screenshot 1](https://raw.githubusercontent.com/or4cu1o/docops-docker-monitor/main/public/screenshots/screenshot-01.png)

![DocOps Screenshot 2](https://raw.githubusercontent.com/or4cu1o/docops-docker-monitor/main/public/screenshots/screenshot-02.png)

## 🚀 Como Executar

### Pré-requisitos

É obrigatório possuir o **Docker Compose V2** instalado.

> [Documentação oficial de instalação do Docker](https://docs.docker.com/compose/install/)

### 1. Criar o manifesto

Crie um arquivo `docker-compose.yml` com o conteúdo abaixo:

```yaml
services:
  docops:
    image: or4cu1o/docops:latest
    container_name: docops
    ports:
      - "8000:8000"
    environment:
      - DOCOPS_USER=admin # Defina seu usuário
      - DOCOPS_PASS=admin # Defina sua senha
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/host/root:ro
    restart: unless-stopped
```

### 2. Iniciar e Acessar

```bash
docker compose up -d
```

Acesse via: `http://localhost:8000` (ou o IP da sua VPS).

---
