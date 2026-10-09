"""
DDNS_Ahnlich API Service
Author: Crizonic-code
FastAPI-based DDNS update API with PowerDNS backend
"""

import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
import requests

from models import User, CreateUser, UpdateDDNS, TokenData, Hostname, CreateHostname

# Configuration
ZONE_NAME = os.getenv("ZONE_NAME", "ddns.dasspec.com")
PDNS_API_URL = os.getenv("PDNS_API_URL", "http://pdns:8081")
PDNS_API_KEY = os.getenv("PDNS_API_KEY", "ddns-secret-api-key-change-me")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 720  # 30 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
DB_PATH = os.getenv("DB_PATH", "/app/data/ddns.db")

app = FastAPI(
    title="DDNS_Ahnlich API",
    description="Free DDNS service - Crizonic-code",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn


def init_db(conn):
    """Initialize database tables"""
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Hostnames table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hostnames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            full_domain TEXT NOT NULL UNIQUE,
            ip_address TEXT,
            last_updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Update logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS update_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname_id INTEGER NOT NULL,
            old_ip TEXT,
            new_ip TEXT,
            user_agent TEXT,
            ip_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hostname_id) REFERENCES hostnames(id)
        )
    """)

    # Donation tracking (optional)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT DEFAULT 'USD',
            method TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_pdns_zone_id(conn, zone_name: str) -> str:
    """Get or create the DNS zone in PowerDNS"""
    headers = {"X-API-Key": PDNS_API_KEY}

    # Check if zone exists
    response = requests.get(
        f"{PDNS_API_URL}/api/v1/servers/localhost/zones/{zone_name}",
        headers=headers
    )

    if response.status_code == 404:
        # Create zone
        zone_data = {
            "name": zone_name,
            "kind": "Native",
            "type": "SOA",
            "soa": {
                "mname": "ns1.ddns.dasspec.com.",
                "hostmaster": "admin.ddns.dasspec.com.",
                "serial": 1,
                "refresh": 3600,
                "retry": 900,
                "expire": 604800,
                "minimum-ttl": 3600
            }
        }
        response = requests.post(
            f"{PDNS_API_URL}/api/v1/servers/localhost/zones",
            headers=headers,
            json=zone_data
        )
        if response.status_code == 201:
            return zone_name
        raise HTTPException(status_code=500, detail=f"Failed to create zone: {response.text}")

    if response.status_code == 200:
        return response.json()["id"]

    raise HTTPException(status_code=500, detail=f"PDNS error: {response.status_code}")


def update_dns_record(conn, full_domain: str, ip: str):
    """Update A record in PowerDNS"""
    headers = {"X-API-Key": PDNS_API_KEY}
    zone_id = get_pdns_zone_id(conn, ZONE_NAME)

    # Get current records
    response = requests.get(
        f"{PDNS_API_URL}/api/v1/servers/localhost/zones/{zone_id}",
        headers=headers
    )
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get zone")

    records = response.json()["rrsets"]

    # Find or create the record
    record_name = full_domain + "."
    record_exists = False

    for i, rrset in enumerate(records):
        if rrset["name"] == record_name and rrset["type"] == "A":
            # Update existing
            records[i]["records"] = [{"content": ip}]
            records[i]["change"] = True
            record_exists = True
            break

    if not record_exists:
        # Create new record
        new_record = {
            "name": record_name,
            "type": "A",
            "ttl": 300,
            "records": [{"content": ip}],
            "changetype": "REPLACE"
        }
        records.append(new_record)

    # Update serial
    zone_data = response.json()
    zone_data["serial"] = zone_data.get("serial", 1) + 1

    # Apply changes
    response = requests.patch(
        f"{PDNS_API_URL}/api/v1/servers/localhost/zones/{zone_id}",
        headers=headers,
        json={"rrsets": records}
    )

    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=500, detail=f"PDNS update failed: {response.text}")


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.close()


# ==================== Auth Endpoints ====================

@app.post("/api/register", response_model=User)
async def register(user: CreateUser):
    """Register a new user account"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create user
    password_hash = get_password_hash(user.password)
    api_key = f"ddns_{secrets.token_urlsafe(32)}"

    cursor.execute(
        "INSERT INTO users (username, password_hash, api_key, email) VALUES (?, ?, ?, ?)",
        (user.username, password_hash, api_key, user.email)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return User(id=user_id, username=user.username, email=user.email, api_key=api_key)


@app.post("/api/login")
async def login(username: str, password: str):
    """Login and get JWT token"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["username"], "user_id": user["id"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


# ==================== DDNS Endpoints ====================

@app.post("/api/update")
async def update_ddns(
    hostname: str,
    ip: Optional[str] = None,
    apikey: Optional[str] = Header(None),
    X_API_Key: Optional[str] = Header(None)
):
    """
    Update DDNS record for a hostname.

    Supports:
    - Query params: hostname, ip
    - Header: apikey or X-API-Key for auth
    - Auto-detect IP from request if not provided
    """
    api_key = apikey or X_API_Key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required (apikey header)")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Authenticate
    cursor.execute("SELECT id FROM users WHERE api_key = ?", (api_key,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid API key")

    user_id = user["id"]

    # Get client IP if not provided
    client_ip = ip
    if not client_ip:
        client_ip = "auto-detected"  # Would use X-Forwarded-For in production

    # Find hostname
    cursor.execute(
        "SELECT * FROM hostnames WHERE name = ? AND user_id = ?",
        (hostname, user_id)
    )
    hostname_record = cursor.fetchone()

    if not hostname_record:
        # Try to create it
        full_domain = f"{hostname}.{ZONE_NAME}"
        cursor.execute(
            "SELECT id FROM hostnames WHERE full_domain = ?",
            (full_domain,)
        )
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Hostname {hostname} already exists")

        cursor.execute(
            "INSERT INTO hostnames (user_id, name, full_domain, ip_address) VALUES (?, ?, ?, ?)",
            (user_id, hostname, full_domain, client_ip)
        )
        hostname_record = cursor.execute(
            "SELECT * FROM hostnames WHERE full_domain = ?", (full_domain,)
        ).fetchone()

    old_ip = hostname_record["ip_address"]
    full_domain = hostname_record["full_domain"]

    # Update if IP changed
    if old_ip != client_ip:
        try:
            update_dns_record(conn, full_domain, client_ip)

            # Log the update
            cursor.execute(
                "INSERT INTO update_logs (hostname_id, old_ip, new_ip) VALUES (?, ?, ?)",
                (hostname_record["id"], old_ip, client_ip)
            )

            # Update hostname record
            cursor.execute(
                "UPDATE hostnames SET ip_address = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?",
                (client_ip, hostname_record["id"])
            )
            conn.commit()

            return {"status": "nochg", "hostname": full_domain, "ip": client_ip}
        except Exception as e:
            conn.rollback()
            conn.close()
            raise HTTPException(status_code=500, detail=f"DNS update failed: {str(e)}")

    conn.close()
    return {"status": "good", "hostname": full_domain, "ip": client_ip}


# ==================== User Management ====================

def get_current_user(X_JWT_Token: str = Header(...)) -> dict:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(X_JWT_Token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"username": payload["sub"], "user_id": payload["user_id"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/api/me", response_model=User)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, api_key, created_at FROM users WHERE id = ?", (user["user_id"],))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return User(id=row["id"], username=row["username"], email=row["email"], api_key=row["api_key"])


@app.get("/api/hostnames", response_model=list[Hostname])
async def list_hostnames(user: dict = Depends(get_current_user)):
    """List user's hostnames"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hostnames WHERE user_id = ? ORDER BY created_at DESC", (user["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    return [
        Hostname(
            id=r["id"],
            name=r["name"],
            full_domain=r["full_domain"],
            ip_address=r["ip_address"],
            last_updated=r["last_updated"],
            created_at=r["created_at"]
        )
        for r in rows
    ]


@app.post("/api/hostnames", response_model=Hostname)
async def create_hostname(hostname: CreateHostname, user: dict = Depends(get_current_user)):
    """Create a new hostname for the user"""
    full_domain = f"{hostname.name}.{ZONE_NAME}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM hostnames WHERE full_domain = ?", (full_domain,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"Hostname {full_domain} already exists")

    cursor.execute(
        "INSERT INTO hostnames (user_id, name, full_domain) VALUES (?, ?, ?)",
        (user["user_id"], hostname.name, full_domain)
    )
    hostname_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return Hostname(
        id=hostname_id,
        name=hostname.name,
        full_domain=full_domain,
        ip_address=None,
        last_updated=None,
        created_at=datetime.utcnow().isoformat()
    )


# ==================== Health ====================

@app.get("/health")
async def health():
    return {"status": "ok", "service": "DDNS_Ahnlich"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
