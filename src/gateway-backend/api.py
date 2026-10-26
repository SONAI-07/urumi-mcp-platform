from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import secrets

from database import get_db
from models import User, MCPServer, AuditLog
from agent import run_agent

app = FastAPI(title="Urumi Gateway API")

# type: ignore is required because PyCharm's type checker doesn't understand FastAPI's dynamic middleware signature
app.add_middleware(  # type: ignore
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- AUTH HELPER ---
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API Key")

    raw_key = authorization.split(" ")[1]
    users = db.query(User).filter(User.is_active == True).all()
    for user in users:
        if pwd_context.verify(raw_key, user.api_key_hash):
            return user

    raise HTTPException(status_code=401, detail="Invalid or Revoked API Key")

# --- SERVER MANAGEMENT ---
class ServerCreate(BaseModel):
    name: str
    url: str

@app.get("/admin/servers")
def list_servers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403, "Admins only")
    return db.query(MCPServer).all()

@app.post("/admin/servers")
def create_server(req: ServerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403, "Admins only")
    srv = MCPServer(name=req.name, url=req.url, is_enabled=True)
    db.add(srv); db.commit()
    return srv

@app.patch("/admin/servers/{server_id}/toggle")
def toggle_server(server_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403, "Admins only")
    srv = db.get(MCPServer, server_id)
    if not srv: raise HTTPException(404, "Server not found")
    srv.is_enabled = not srv.is_enabled
    db.commit()
    return srv

# --- USER MANAGEMENT ---
class UserCreate(BaseModel):
    username: str
    role: str = "member"

@app.post("/admin/users")
async def create_user(req: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403, "Admins only")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(409, "User exists")
    raw = secrets.token_hex(32)
    db.add(User(username=req.username, api_key_hash=pwd_context.hash(raw), is_active=True, role=req.role))
    db.commit()
    return {"username": req.username, "api_key": raw}

@app.post("/admin/users/{user_id}/revoke")
async def revoke_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403, "Admins only")
    target = db.get(User, user_id)
    if not target: raise HTTPException(404, "No such user")
    target.is_active = False
    db.commit()
    return {"revoked": target.username}

# --- AUDIT LOGS ---
@app.get("/admin/audit-logs")
def list_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403, "Admins only")
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()

# --- CHAT AGENT ---
class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/agent/chat")
async def agent_chat(req: ChatRequest, authorization: str = Header(None), current_user: User = Depends(get_current_user)):
    # Extract the raw key to pass to the agent so it can authenticate its MCP calls as this user
    raw_key = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else ""
    return await run_agent(req.message, req.history, raw_key)