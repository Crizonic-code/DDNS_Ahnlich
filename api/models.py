"""
DDNS_Ahnlich API Models
"""

from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    api_key: str
    created_at: Optional[str] = None


class CreateUser(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class Hostname(BaseModel):
    id: int
    name: str
    full_domain: str
    ip_address: Optional[str] = None
    last_updated: Optional[str] = None
    created_at: Optional[str] = None


class CreateHostname(BaseModel):
    name: str


class UpdateDDNS(BaseModel):
    hostname: str
    ip: Optional[str] = None


class TokenData(BaseModel):
    username: str
    user_id: int
