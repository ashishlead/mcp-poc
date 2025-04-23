import json
import os
from typing import Dict, Any, List

def load_json_file(file_path: str) -> Dict:
    """Load JSON data from a file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json_file(file_path: str, data: Dict) -> None:
    """Save JSON data to a file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def format_tool_result(result: Any) -> str:
    """Format a tool result for LLM consumption"""
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2)
    return str(result)

def parse_function_args(args_str: str) -> Dict:
    """Parse function arguments from a string"""
    try:
        return json.loads(args_str)
    except json.JSONDecodeError:
        return {}

def get_env_var(name: str, default: str = None) -> str:
    """Get an environment variable with a default value"""
    return os.environ.get(name, default)
