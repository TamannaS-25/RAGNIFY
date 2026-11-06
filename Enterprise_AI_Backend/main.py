from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import os

from database import engine, Base
import models

# Create all database tables and seed initial data
Base.metadata.create_all(bind=engine)
try:
    from seed_database import seed_all
    seed_all()
except Exception as e:
    print(f"Database seed notice: {e}")

# Import Routers
from routers import auth
from routers import dashboard
from routers import employees
from routers import managers
from routers import tasks
from routers import employee_dashboard
from routers import employee_tasks
from routers import rag
from routers import ai_assistant
from routers import meeting
from routers import onboarding
from routers import documents
from routers import offer_letters
from routers import certificates
from routers import tenure
from routers import notifications

app = FastAPI(
    title="RAGNIFY Enterprise AI & HR Backend",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories
DOCS_DIR = os.path.join(os.path.dirname(__file__), "uploads", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)
app.mount("/static/documents", StaticFiles(directory=DOCS_DIR), name="documents")

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "uploads", "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
app.mount("/static/generated_reports", StaticFiles(directory=REPORTS_DIR), name="generated_reports")

# Register Routers
app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(tasks.router)
app.include_router(managers.router)
app.include_router(dashboard.router)
app.include_router(employee_dashboard.router)
app.include_router(employee_tasks.router)
app.include_router(onboarding.router)
app.include_router(documents.router)
app.include_router(offer_letters.router)
app.include_router(certificates.router)
app.include_router(tenure.router)
app.include_router(rag.router)
app.include_router(ai_assistant.router)
app.include_router(meeting.router)
app.include_router(notifications.router)

# Home Route
@app.get("/")
def home():
    return {
        "message": "Welcome to RAGNIFY Enterprise AI & HR Onboarding Backend!",
        "version": "2.0.0",
        "status": "Operational"
    }

# Database Connection Test
@app.get("/test-db")
def test_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "message": "Database Connected Successfully to Task Management PostgreSQL!"
        }
    except Exception as e:
        return {
            "error": str(e)
        }