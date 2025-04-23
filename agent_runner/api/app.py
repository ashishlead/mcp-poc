from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from agent_runner.api.router import router
from agent_runner.db.database import get_db, engine
from agent_runner.db.models import Base
from agent_runner.utils.litellm_client import configure_litellm

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Configure LiteLLM
configure_litellm()

# Create FastAPI app
app = FastAPI(
    title="Agent Runner API",
    description="API for managing and running LLM agent workspaces",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to Agent Runner API"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Check database connection
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }
