from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./reading_assessment.db"

# SQLite needs check_same_thread=False for FastAPI usage.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency to provide a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
