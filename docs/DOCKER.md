# Docker Deployment Guide

HannaIRC is designed to run in Docker with Docker Compose, providing a complete containerized n8n environment with integrated IRC bot service.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        nginx (TLS)                          │
│                   (Reverse Proxy + SSL)                     │
└──────────────┬──────────────────────────────────────────────┘
               │
         ┌─────┴──────┐
         ▼             ▼
    ┌────────┐    ┌──────────┐
    │ n8n    │    │  Qdrant  │
    │(5678)  │    │ (6333)   │
    └────┬───┘    └────▲─────┘
         │             │
         └──┬──────────┘
            │
    ┌───────┴────────┐
    ▼                ▼
┌────────────┐  ┌────────────┐
│ PostgreSQL │  │ hanna-bot  │
│ (5432)     │  │ (8080)     │
└────────────┘  └────────────┘
```

## Services

| Service | Purpose | Port | Image |
|---------|---------|------|-------|
| **n8n** | Workflow engine | 5678 | n8n-custom or n8nio/n8n |
| **PostgreSQL** | n8n database | 5432 | postgres:16 |
| **Qdrant** | Vector database | 6333 | qdrant/qdrant |
| **nginx** | Reverse proxy + TLS | 80, 443 | nginx:stable |
| **hanna-bot** | IRC bot | 8080 | hanna-bot (custom) |

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Pontuzz/HannaIRC.git
cd HannaIRC
```

### 2. Create Production Compose File

```bash
cp docs/docker-compose.example.yml docker-compose.yml
```

### 3. Configure Environment

Edit `docker-compose.yml` and replace placeholders:
- `CHANGE_ME_PASSWORD` → Strong PostgreSQL password
- `CHANGE_ME_TOKEN` → Random API tokens
- `example.com` → Your domain
- `irc.example.com` → IRC server address
- SSL certificate paths

### 4. Set Up SSL Certificates

```bash
# Copy your certificates to a secure location
mkdir -p ./certs
cp /path/to/your/cert.pem ./certs/
cp /path/to/your/key.key ./certs/
```

Update paths in `docker-compose.yml`:
```yaml
volumes:
  - ./certs/cert.pem:/qdrant/certs/hivenet.pem
  - ./certs/key.key:/qdrant/certs/hivenet.dev.key
```

### 5. Create Networks (if needed)

```bash
# If using external networks
docker network create n8n_network
docker network create hanna_network
```

### 6. Start Services

```bash
docker-compose up -d

# Check logs
docker-compose logs -f n8n
```

## Configuration

### PostgreSQL

Store n8n data and chat history. Must be accessible by n8n service.

**Environment Variables:**
- `POSTGRES_USER` - Database user (default: n8n)
- `POSTGRES_PASSWORD` - Strong password (generate with `openssl rand -base64 32`)
- `POSTGRES_DB` - Database name (default: n8n)

### n8n

Main workflow engine. Runs HannaIRC, HannaLearns, TeachHanna workflows.

**Key Environment Variables:**
- `DB_TYPE: postgresdb` - Use PostgreSQL
- `N8N_HOST` - Your domain (e.g., n8n.example.com)
- `N8N_PROTOCOL: https` - Always use HTTPS
- `WEBHOOK_URL` - Public webhook URL
- `TZ` - Timezone for schedules

**Import Workflows:**
1. Log into n8n UI
2. Menu → Workflows → Import
3. Select workflow JSON files from `docs/examples/`
4. Configure credentials (OpenAI, SerpAPI, Qdrant, etc.)

### Qdrant

Vector database for knowledge storage. TLS is recommended for production.

**Environment Variables:**
- `QDRANT__SERVICE__API_TLS_CERT` - Path to certificate
- `QDRANT__SERVICE__API_TLS_KEY` - Path to private key

**Create Collections:**
Access Qdrant Web UI at `https://your-domain:6334/dashboard`:

```json
Collection: hannabot_knowledge
Vector size: 1536
Distance: Cosine
```

### IRC Bot (hanna-bot)

Connects to IRC server and sends events to n8n.

**Environment Variables:**
- `IRC_ADDR` - IRC server (irc.libera.chat:6697)
- `IRC_NICK` - Bot nickname
- `IRC_TLS` - Enable TLS (1 or 0)
- `SASL_USER` / `SASL_PASS` - Authentication
- `AUTOJOIN` - Channel to join (#HiveNet)
- `N8N_WEBHOOK` - n8n IRC trigger URL
- `API_ADDR` - Bot API address (:8080)
- `API_TOKEN` - Secure token for API access

### nginx Configuration

Handles TLS termination and routing to n8n + Qdrant.

**Use the example configuration:**
```bash
cp docs/nginx.conf.example ./nginx.conf
# Edit nginx.conf:
# - Replace example.com with your domain
# - Update certificate paths
# - Set correct webhook IDs
```

**Full configuration reference:**
See [docs/nginx.conf.example](nginx.conf.example) for:
- n8n workflows proxy (port 5678)
- Qdrant vector database proxy (port 6333)
- Hanna bot UI and API proxies
- TLS/SSL setup
- CORS configuration for internal services
- HTTP to HTTPS redirects
- Health check endpoints

**Create `nginx.conf`:**
```nginx
upstream n8n {
    server n8n:5678;
}

upstream qdrant {
    server qdrant:6333;
}

server {
    listen 443 ssl http2;
    server_name n8n.example.com;
    
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://n8n;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}

server {
    listen 443 ssl http2;
    server_name qdrant.example.com;
    
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.key;
    
    location / {
        proxy_pass https://qdrant:6333;
        proxy_ssl_verify off;
    }
}
```

## Persistence

All data is persisted in Docker volumes:

```yaml
volumes:
  n8n_data:              # n8n workflows and settings
  n8n_postgres_data:     # Chat history and configuration
  qdrant_data:           # Vector embeddings
```

**Backup volumes:**
```bash
docker run --rm -v n8n_data:/data -v $(pwd):/backup ubuntu tar czf /backup/n8n_data.tar.gz /data
docker run --rm -v qdrant_data:/data -v $(pwd):/backup ubuntu tar czf /backup/qdrant_data.tar.gz /data
```

## Monitoring

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f n8n
docker-compose logs -f hanna-bot
```

### Health Checks

Each service has health monitoring:

```bash
# Check container status
docker-compose ps

# Inspect n8n health
docker exec n8n curl -s http://localhost:5678/healthz
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Qdrant TLS error** | Verify cert paths match container paths; check certificate validity |
| **n8n can't connect to PostgreSQL** | Check `depends_on`, verify password in both places |
| **Bot not receiving events** | Verify webhook URL is public and accessible; check n8n logs |
| **Port conflicts** | Change ports in compose file (e.g., `8443:443` for nginx) |
| **Memory issues** | Increase Docker memory limits; reduce n8n worker count |

## Security Best Practices

1. **Use strong credentials:**
   ```bash
   openssl rand -base64 32  # Generate passwords
   ```

2. **Isolate secrets:**
   - Use Docker secrets or `.env` file (add to `.gitignore`)
   - Never commit docker-compose.yml with real credentials

3. **Network isolation:**
   - Use bridge networks for service-to-service communication
   - Don't expose unnecessary ports

4. **TLS certificates:**
   - Use valid SSL certificates (Let's Encrypt recommended)
   - Renew before expiration

5. **Regular backups:**
   ```bash
   # Backup volumes
   docker-compose exec postgres pg_dump -U n8n n8n | gzip > backup.sql.gz
   ```

## Upgrading Services

Update image tags and restart:

```bash
# Update n8n
docker-compose pull n8n
docker-compose up -d n8n

# Check logs
docker-compose logs -f n8n
```

## Production Deployment

1. **Use a `.env` file** for sensitive variables:
   ```bash
   # .env (gitignore'd)
   DB_PASSWORD=your_strong_password
   API_TOKEN=your_secure_token
   ```

2. **Update compose file:**
   ```yaml
   environment:
     POSTGRES_PASSWORD: ${DB_PASSWORD}
   ```

3. **Run with environment file:**
   ```bash
   docker-compose --env-file .env up -d
   ```

4. **Set up log rotation:**
   ```json
   {
     "log-driver": "json-file",
     "log-opts": {
       "max-size": "10m",
       "max-file": "3"
     }
   }
   ```

## Useful Commands

```bash
# Start in background
docker-compose up -d

# Stop all services
docker-compose down

# Recreate containers
docker-compose up -d --force-recreate

# View volumes
docker volume ls

# Clean up unused volumes
docker volume prune

# Access n8n shell
docker-compose exec n8n bash

# Check database
docker-compose exec postgres psql -U n8n -d n8n
```

## Support

For issues or questions:
- Check logs: `docker-compose logs <service>`
- See [SETUP.md](SETUP.md) for configuration details
- Visit [botinfo.hivenet.dev](https://botinfo.hivenet.dev)
