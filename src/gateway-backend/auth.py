from passlib.context import CryptContext
from database import SessionLocal
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def authenticate_raw_key(raw_key: str):
    """Return the username if the raw key matches an active user's hash."""
    if not raw_key:
        return None
    db = SessionLocal()
    try:
        for user in db.query(User).filter(User.is_active == True).all():
            if pwd_context.verify(raw_key, user.api_key_hash):
                return user.username
        return None
    finally:
        db.close()