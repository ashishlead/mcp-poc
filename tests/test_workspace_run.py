import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow importing from agent_runner
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runner.core.workspace import WorkspaceManager
from agent_runner.utils.litellm_client import configure_litellm
from agent_runner.db.database import get_db, engine
from agent_runner.db.models import Base

# Initialize database and configure LiteLLM
load_dotenv()
configure_litellm()
Base.metadata.create_all(bind=engine)

# Sample workspace JSON for testing
SAMPLE_WORKSPACE = {
    "Test Agent@v1#details": {
        "steps": [
            {"id": "1. Process", "name": "1. Process"}
        ]
    },
    "Test Agent@v1@step-1. Process#details": {
        "chat": [
            {"role": "system", "content": "You are a helpful AI assistant that can process text and perform calculations."},
            {"role": "user", "content": "Process the following text: 'Hello, world!' and count the characters."}
        ],
        "function": [
            "process_text"
        ],
        "nextStep": "-",
        "model": "openai/gpt-4o",
        "runFunctionsInParallel": False,
        "passConversationToNextStep": False
    },
    "Test Agent@v1@func-process_text#details": {
        "description": "Process text with various operations",
        "parameters": [
            {"type": "string", "name": "text", "description": "The text to process"},
            {"type": "array", "name": "operations", "description": "List of operations to perform (lowercase, uppercase, tokenize, count_words, count_chars)"}
        ],
        "code": "def process_text(text, operations):\n    results = {}\n    \n    for operation in operations:\n        if operation == \"lowercase\":\n            results[\"lowercase\"] = text.lower()\n        elif operation == \"uppercase\":\n            results[\"uppercase\"] = text.upper()\n        elif operation == \"tokenize\":\n            results[\"tokenize\"] = text.split()\n        elif operation == \"count_words\":\n            results[\"count_words\"] = len(text.split())\n        elif operation == \"count_chars\":\n            results[\"count_chars\"] = len(text)\n    \n    return results"
    }
}


async def test_run_workspace():
    """Test running a workspace"""
    print("\n=== Testing Workspace Run ===\n")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create workspace manager
        manager = WorkspaceManager(db)
        
        # Create a new workspace
        print("Creating workspace...")
        workspace = manager.create_workspace(
            name="Test Agent",
            version="v1",
            json_data=SAMPLE_WORKSPACE
        )
        
        print(f"Created workspace with ID: {workspace.db_workspace.id}")
        
        # Run the workspace
        print("\nRunning workspace...")
        run = await workspace.run()
        
        # Print results
        print("\nWorkspace run completed!")
        print("Results:")
        print(json.dumps(run.results, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


async def test_api_client():
    """Test the API client"""
    print("\n=== Testing API Client ===\n")
    
    import aiohttp
    
    # Get API URL from environment or use default
    api_url = os.getenv("API_URL", "http://localhost:9000/api")
    
    async with aiohttp.ClientSession() as session:
        # Test creating a workspace
        print("Creating workspace via API...")
        async with session.post(
            f"{api_url}/workspaces/",
            json={
                "name": "Test API Agent",
                "version": "v1",
                "json_data": SAMPLE_WORKSPACE
            }
        ) as response:
            if response.status == 200:
                workspace_data = await response.json()
                workspace_id = workspace_data.get("id")
                print(f"Created workspace with ID: {workspace_id}")
                
                # Test running the workspace
                print("\nRunning workspace via API...")
                async with session.post(
                    f"{api_url}/workspaces/{workspace_id}/run",
                    json={
                        "workspace_id": workspace_id,
                        "kwargs": {}
                    }
                ) as run_response:
                    if run_response.status == 200:
                        run_data = await run_response.json()
                        run_id = run_data.get("run_id")
                        print(f"Started run with ID: {run_id}")
                        
                        # Wait for run to complete
                        print("Waiting for run to complete...")
                        status = "queued"
                        while status in ["queued", "running"]:
                            await asyncio.sleep(2)
                            async with session.get(f"{api_url}/runs/{run_id}") as status_response:
                                if status_response.status == 200:
                                    status_data = await status_response.json()
                                    status = status_data.get("status")
                                    print(f"Run status: {status}")
                                else:
                                    print(f"Error checking run status: {await status_response.text()}")
                                    break
                        
                        # Print results
                        if status == "completed":
                            print("\nWorkspace run completed!")
                            print("Results:")
                            print(json.dumps(status_data.get("results", {}), indent=2))
                    else:
                        print(f"Error running workspace: {await run_response.text()}")
            else:
                print(f"Error creating workspace: {await response.text()}")


async def main():
    # Choose which test to run
    test_type = input("Which test would you like to run? (1: Direct Run, 2: API Client): ")
    
    if test_type == "2":
        await test_api_client()
    else:
        await test_run_workspace()


if __name__ == "__main__":
    asyncio.run(main())
