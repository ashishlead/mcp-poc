import litellm
from dotenv import load_dotenv
import os

load_dotenv()

# Load LiteLLM configuration from environment variables
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
LITELLM_MODEL_MAP = os.getenv("LITELLM_MODEL_MAP", "{}")

def configure_litellm():
    """Configure LiteLLM with API keys and model mappings"""
    # Set API key
    if LITELLM_API_KEY:
        litellm.api_key = LITELLM_API_KEY
    
    # Set up model mappings if provided
    try:
        import json
        model_map = json.loads(LITELLM_MODEL_MAP)
        for model_name, model_config in model_map.items():
            litellm.model_list.append(model_config)
    except Exception as e:
        print(f"Error configuring LiteLLM model mappings: {e}")
    
    # Configure any additional LiteLLM settings
    litellm.set_verbose = True
    
    # Return the configured litellm module
    return litellm
