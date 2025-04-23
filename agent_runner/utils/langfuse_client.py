from langfuse import Langfuse
from langfuse.client import AsyncClient
from dotenv import load_dotenv
import os

load_dotenv()

# Load Langfuse credentials from environment variables
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

def get_langfuse_client() -> Langfuse:
    """Get a Langfuse client instance"""
    return Langfuse(
        host=LANGFUSE_HOST,
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY
    )

def get_async_langfuse_client() -> AsyncClient:
    """Get an async Langfuse client instance"""
    return AsyncClient(
        host=LANGFUSE_HOST,
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY
    )
