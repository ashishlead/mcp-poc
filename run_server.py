import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get server configuration from environment variables
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9000"))

if __name__ == "__main__":
    print(f"Starting Agent Runner API server at http://{HOST}:{PORT}")
    uvicorn.run(
        "agent_runner.api.app:app",
        host=HOST,
        port=PORT,
        reload=True
    )
