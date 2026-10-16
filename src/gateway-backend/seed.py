from database import engine, SessionLocal, Base
from models import User, MCPServer
from passlib.context import CryptContext
import secrets

# Setup password/key hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 1. Create Admin User
    if not db.query(User).filter(User.username == "admin").first():
        raw_api_key = secrets.token_hex(32)  # Generate a secure random API key
        print(f"\n🔑 ADMIN API KEY (Save this! You will need it for testing): {raw_api_key}")

        admin_user = User(
            username="admin",
            role="admin",
            api_key_hash=pwd_context.hash(raw_api_key),
            is_active=True
        )
        db.add(admin_user)

    # 2. Register the WooCommerce MCP Server
    # (Since it's inside the cluster, the URL is the internal K8s service name!)
    if not db.query(MCPServer).filter(MCPServer.name == "woo-mcp").first():
        # 2. Register the WooCommerce MCP Server
        woo_server = db.query(MCPServer).filter(MCPServer.name == "woo-mcp").first()
        if not woo_server:
            woo_server = MCPServer(
                name="woo-mcp",
                url="http://woo-mcp-server:80/mcp",  # Internal K8s DNS name!
                is_enabled=True
            )
            db.add(woo_server)
        else:
            # Force update the URL in case it was previously seeded with a localhost URL
            woo_server.url = "http://woo-mcp-server:80/mcp"

    db.commit()
    db.close()
    print("✅ Database seeded successfully!")


if __name__ == "__main__":
    seed()