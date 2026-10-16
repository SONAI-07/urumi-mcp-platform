from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import secrets
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware


from database import get_db, SessionLocal
from models import User, MCPServer, AuditLog

app = FastAPI(title="Urumi Gateway API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # local dev; in values-prod we'd whitelist the dashboard origin
    allow_methods=["*"],
    allow_headers=["*"],        # lets the Authorization: Bearer header through
)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- AUTH HELPER ---
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API Key")

    raw_key = authorization.split(" ")[1]
    # Since we only store hashes, we must check against all active users
    users = db.query(User).filter(User.is_active == True).all()
    for user in users:
        if pwd_context.verify(raw_key, user.api_key_hash):
            return user

    raise HTTPException(status_code=401, detail="Invalid or Revoked API Key")


# --- ADMIN ROUTES ---
class MCPServerCreate(BaseModel):
    name: str
    url: str
    auth_header_name: Optional[str] = None
    auth_token: Optional[str] = None


@app.post("/admin/servers")
def add_server(server: MCPServerCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    token_hash = pwd_context.hash(server.auth_token) if server.auth_token else None

    db_server = MCPServer(
        name=server.name,
        url=server.url,
        auth_header_name=server.auth_header_name,
        auth_token_hash=token_hash,
        is_enabled=True
    )
    db.add(db_server)
    db.commit()
    return {"status": "added"}


@app.get("/admin/servers")
def list_servers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return db.query(MCPServer).all()


@app.delete("/admin/servers/{server_id}")
def remove_server(server_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(404, detail="Server not found")
    db.delete(server)
    db.commit()
    return {"status": "deleted"}


@app.patch("/admin/servers/{server_id}/toggle")
def toggle_server(server_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(404)
    server.is_enabled = not server.is_enabled
    db.commit()
    return {"status": "toggled", "is_enabled": server.is_enabled}


# --- TEAM / USER ROUTES ---
@app.post("/users/me/api-key")
def generate_api_key(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    raw_key = secrets.token_hex(32)
    user.api_key_hash = pwd_context.hash(raw_key)
    db.commit()
    return {"api_key": raw_key}


@app.get("/admin/audit-logs")
def get_logs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()