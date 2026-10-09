# DDNS_Ahnlich — Self-hosted DDNS Service (Like No-IP/DuckDNS)

**Status:** Planned  
**Target Hosting:** IONOS VPS/Cloud  
**Business Model:** Free / Donation only  
**Author:** Crizonic-code  

---

## Infrastructure

- **Platform:** IONOS Linux VPS (minimum 1 vCPU / 1GB RAM / 20GB SSD)
- **Estimated Cost:** ~3-5 EUR/month
- **Domain:** ddns.dasspec.com
- **DNS:** Authoritative nameservers on the VPS (managed via IONOS)

---

## Architecture

### Core Components

1. **Authoritative DNS Server**
   - Software: BIND9 or PowerDNS (PDNS preferred for API integration)
   - Manages zone: `*.ddns.dasspec.com`
   - Supports dynamic record updates via API

2. **DDNS Update API**
   - Endpoint: `POST https://api.ddns.dasspec.com/update`
   - Parameters:
     - `user` or `apikey`: authentication
     - `hostname`: the subdomain to update (e.g., `client1.ddns.dasspec.com`)
     - `ip`: the client's current public IP
   - Validates credentials, updates DNS A record
   - Returns: JSON response (success/failure)

3. **User Database**
   - SQLite (simple) or MySQL/MariaDB (scalable)
   - Tables: users, hostnames, api_keys, logs

4. **Web Admin Panel**
   - Register accounts
   - Assign/manage subdomains
   - View/update API keys
   - Usage logs
   - Tech: Python (Flask/FastAPI) or Node.js

5. **TLS/SSL**
   - Let's Encrypt via Certbot
   - HTTPS on api.ddns.dasspec.com and admin.ddns.dasspec.com

6. **Client Support**
   - ddclient compatible
   - Standard HTTP/HTTPS update endpoint
   - Example commands for curl, cron, systemd service

---

## Authentication Flow

1. User signs up → receives username, password, API key
2. User is assigned one or more hostnames: `theirname.ddns.dasspec.com`
3. Client on user's device calls API with API key + hostname
4. Server validates, updates A record, logs the change

---

## Security Considerations

- Rate limiting on update API (prevent abuse)
- API keys hashed in database
- HTTPS only (no plaintext updates)
- Optional 2FA for admin panel
- Input validation on hostname/IP fields

---

## Development Phases

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| 1 | Provision IONOS VPS, setup OS, firewall | 2-4 hours |
| 2 | Install & configure DNS server (PDNS/BIND) | 1 day |
| 3 | Build DDNS update API + database | 2-3 days |
| 4 | Build web admin panel | 2-3 days |
| 5 | SSL, reverse proxy (Nginx), hardening | 1 day |
| 6 | Testing, documentation, client examples | 1-2 days |

**Total:** ~1-2 weeks of active development

---

## Example Client Configurations

### ddclient
```
protocol=custom
server=api.ddns.dasspec.com
login=USER_API_KEY
password=USER_PASSWORD
path=/update
host=myhost.ddns.dasspec.com
```

### Cron + curl
```
*/5 * * * * curl -s "https://api.ddns.dasspec.com/update?key=APIKEY&host=myhost.ddns.dasspec.com"
```

### Windows Task Scheduler
```
curl -s "https://api.ddns.dasspec.com/update?key=APIKEY&host=myhost.ddns.dasspec.com"
```

---

## Donation Integration (Optional)

- Buy Me a Coffee / Ko-fi button on admin panel
- Optional: longer hostname length or more hostnames for donors
- Keep it simple — free for everyone

---

## Notes

- Separate project from unobligated-armory / Raspberry Pi VPN server
- This is the DDNS *provider* infrastructure
- Pi uses this service (or IONOS built-in DDNS) for its own dynamic IP
