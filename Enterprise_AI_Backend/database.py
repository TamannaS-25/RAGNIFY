import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = None

if DATABASE_URL:
    try:
        connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        test_engine = create_engine(DATABASE_URL, connect_args=connect_args)
        with test_engine.connect() as conn:
            pass
        engine = test_engine
    except Exception as e:
        print(f"[Database] Configured DATABASE_URL failed: {e}")

if engine is None:
    # Try default PostgreSQL
    password = quote_plus("Shreya@8767")
    pg_url = f"postgresql://postgres:{password}@localhost:5432/Task Management"
    try:
        test_engine = create_engine(pg_url)
        with test_engine.connect() as conn:
            pass
        engine = test_engine
        DATABASE_URL = pg_url
        print("[Database] Connected successfully to PostgreSQL!")
    except Exception as e:
        # Fallback to local SQLite database
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_path = os.path.join(backend_dir, "ragnify.db")
        DATABASE_URL = f"sqlite:///{sqlite_path}"
        print(f"[Database] PostgreSQL unavailable ({e}). Falling back to SQLite: {DATABASE_URL}")
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
