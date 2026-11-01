import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://urumi:urumi_pass@gateway-db:5432/gateway"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# THIS IS THE MISSING PIECE FASTAPI NEEDS
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()