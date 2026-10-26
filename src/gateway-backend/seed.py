import secrets
from passlib.context import CryptContext
from database import SessionLocal, engine, Base  # <-- Import engine and Base!
from models import User, MCPServer
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    # CREATE TABLES IF THEY DON'T EXIST (Crucial for an empty PVC!)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Admin User
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            raw_api_key = secrets.token_hex(32)
            admin = User(
                username="admin",
                api_key_hash=pwd_context.hash(raw_api_key),
                is_active=True,
                role="admin"
            )
            db.add(admin)
            db.commit()
            print(f"\n🔑 ADMIN API KEY (Save this! You will need it for testing): {raw_api_key}\n")

        # 2. Member User (User B)
        member = db.query(User).filter(User.username == "member").first()
        if not member:
            member_key = secrets.token_hex(32)
            member = User(
                username="member",
                api_key_hash=pwd_context.hash(member_key),
                is_active=True,
                role="member"
            )
            db.add(member)
            db.commit()
            print(f"\n🔑 MEMBER API KEY (User B - Save this!): {member_key}\n")

        # 3. Register MCP Server
        woo_server = db.query(MCPServer).filter(MCPServer.name == "woo-mcp").first()
        woo_url = os.environ.get("UPSTREAM_WOO_URL", "http://woo-mcp-server:80/mcp")
        if not woo_server:
            woo_server = MCPServer(name="woo-mcp", url=woo_url, is_enabled=True)
            db.add(woo_server)
        else:
            woo_server.url = woo_url
        db.commit()
        print("✅ Database seeded successfully.")
    finally:
        db.close()
        # 4. Two additional public upstreams (filesystem + everything-server)


    for name, url in [
    ("fs-mcp", os.environ.get("UPSTREAM_FS_URL", "http://fs-mcp:80/mcp")),
    ("all-mcp", os.environ.get("UPSTREAM_ALL_URL", "http://all-mcp:80/mcp")),
]:
        srv = db.query(MCPServer).filter(MCPServer.name == name).first()
        if not srv:
         db.add(MCPServer(name=name, url=url, is_enabled=True))
    db.commit()
if __name__ == "__main__":
    seed()