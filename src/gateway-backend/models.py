from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    api_key_hash = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="member")   # ← ADD THIS LINE if missing

class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=False)

    # Optional static credential (header or bearer token)
    auth_header_name = Column(String, nullable=True)
    auth_token_hash = Column(String, nullable=True)  # Stored hashed for security!

    is_enabled = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String, nullable=True)  # Denormalized for easy querying

    server_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)

    duration_ms = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)