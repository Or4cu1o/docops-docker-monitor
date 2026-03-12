# 🐋 DocOps (Docker Monitor for DevOps)

Painel de telemetria _Enterprise-Grade_ para VPS Linux. Desenvolvido para entregar visibilidade de borda (Edge Observability) com latência zero, consumo ínfimo de recursos e segurança inviolável.

## 🛡️ Arquitetura de Segurança
- **Zero-Shell:** O motor não executa comandos de terminal. Lê o hardware através de arquivos `/proc` montados como Somente Leitura (`:ro`).
- **Monolito Modular:** Separação estrita entre a API (Backend) e a Interface (Frontend).
- **Stateful Auth:** Sessões criptografadas mantidas na RAM com cookies `HttpOnly`. Nenhuma injeção XSS pode roubar a sessão.

## 🚀 Implantação
Utilize o `docker-compose.yml` providenciado neste repositório e execute:
`docker compose up -d`
