import uvicorn
import os
from dotenv import load_dotenv

from agent_runner.api.app import app
from agent_runner.db.models import init_db
from agent_runner.utils.litellm_client import configure_litellm

# Load environment variables
load_dotenv()

# Configure LiteLLM
configure_litellm()

# Initialize database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_runner.db")
init_db(DATABASE_URL)

def start_server():
    """Start the FastAPI server"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "agent_runner.api.app:app",
        host=host,
        port=port,
        reload=True
    )

if __name__ == "__main__":
    start_server()
