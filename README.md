# DDNS_Ahnlich — Free DDNS Service (Like DuckDNS/No-IP)

**Author:** Crizonic-code  
**Status:** Scaffolded — ready to deploy on IONOS VPS  
**License:** MIT (intended)

---

## Architecture

```
ddns.dasspec.com (IONOS VPS)
├── nginx          — Reverse proxy + TLS termination
├── pdns           — PowerDNS Authoritative (manages DNS records)
├── api            — FastAPI service (auth, DDNS updates, user mgmt)
└── web            — React frontend (user dashboard)
```

## Tech Stack

| Component | Tech |
|-----------|------|
| DNS Server | PowerDNS Authoritative (gsqlite3) |
| API | Python FastAPI + SQLite |
| Frontend | React + Vite |
| Proxy | Nginx |
| Containerization | Docker + docker-compose |

## Quick Start (IONOS VPS)

### Prerequisites
- IONOS Linux VPS (Ubuntu 24.04 recommended)
- Docker + Docker Compose installed
- Domain: ddns.dasspec.com pointing to VPS IP

### Deploy

```bash
# Clone to VPS
git clone https://github.com/Crizonic-code/DDNS_Ahnlich.git
cd DDNS_Ahnlich

# Generate secrets
export PDNS_API_KEY=$(openssl rand -hex 32)
export JWT_SECRET=$(openssl rand -hex 32)

# Build and start
docker compose up -d --build

# Get SSL cert (adjust domain)
docker exec ddns-nginx certbot certonly --nginx -d ddns.dasspec.com

# Restart nginx with SSL
docker compose restart nginx
```

### Access
- Web UI: https://ddns.dasspec.com
- API: https://ddns.dasspec.com/api/
- PowerDNS API: http://localhost:8081/api/v1/servers/localhost

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/register | Create account |
| POST | /api/login | Get JWT token |
| GET | /api/me | Current user info |
| POST | /api/update?hostname=X&apikey=Y | Update DDNS record |
| GET | /api/hostnames | List user's hostnames |
| POST | /api/hostnames | Create new hostname |
| GET | /health | Health check |

## DDNS Client Examples

### curl
```bash
curl -H "apikey: YOUR_API_KEY" \
  "https://ddns.dasspec.com/api/update?hostname=myhost"
```

### ddclient
```
protocol=dyndns2
server=ddns.dasspec.com
login=myhost
password=YOUR_API_KEY
myhost.ddns.dasspec.com
```

### Cron (every 5 min)
```
*/5 * * * * curl -s -H "apikey: YOUR_API_KEY" \
  "https://ddns.dasspec.com/api/update?hostname=myhost"
```

## File Structure

```
DDNS_Ahnlich/
├── docker-compose.yml       — Container orchestration
├── pdns.conf               — PowerDNS config
├── api/
│   ├── Dockerfile
│   ├── main.py             — FastAPI app
│   ├── models.py           — Pydantic models
│   └── requirements.txt
├── web/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx         — React UI
│       └── styles.css
└── nginx/
    └── nginx.conf          — Reverse proxy config
```

## Security Notes

- Change default JWT_SECRET and PDNS_API_KEY before deploying
- Enable HTTPS (SSL certs via Let's Encrypt)
- Consider rate limiting on /api/update
- SQLite is fine for small scale; migrate to PostgreSQL for production scale

## Donation (Optional)

Service is free. If you'd like to support development:
- [Buy Me a Coffee](https://buymeacoffee.com/crizonic) (add your link)

---

*"We don't settle for right."* — UnobligatedRascal / Crizonic-code
