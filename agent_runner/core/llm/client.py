import json
import time
from typing import Dict, List, Any, Optional
import litellm

from langfuse import Langfuse
from langfuse.api.client import AsyncFernLangfuse


async def call_llm(model: str, messages: List[Dict], tools: Optional[List] = None, trace_id: Optional[str] = None, span_id: Optional[str] = None):
    """Call LLM with tools and return the response
    
    Args:
        model: The model to use
        messages: The conversation history
        tools: Optional tools to provide to the LLM
        trace_id: Optional Langfuse trace ID
        span_id: Optional Langfuse span ID
        
    Returns:
        The LLM response
    """
    metadata = {}
    if trace_id and span_id:
        metadata["langfuse"] = {
            "trace_id": trace_id,
            "span_id": span_id
        }
    
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        tools=tools if tools else None,
        tool_choice="auto" if tools else None,
        metadata=metadata
    )
    
    return response


def build_tools_array(function_details: Dict, available_functions: List) -> List[Dict]:
    """Build the tools array for LLM
    
    Args:
        function_details: Dictionary of function details
        available_functions: List of available function names
        
    Returns:
        List of tool objects for LLM
    """
    tools = []
    
    for func_name in available_functions:
        func_detail = function_details.get(func_name, {})
        
        if func_detail:
            tool = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": func_detail.get('description', ''),
                    "parameters": convert_parameters_to_schema(func_detail.get('parameters', []))
                }
            }
            tools.append(tool)
    
    return tools


def convert_parameters_to_schema(parameters: List[Dict]) -> Dict:
    """Convert parameters list to JSON Schema
    
    Args:
        parameters: List of parameter dictionaries
        
    Returns:
        JSON Schema object
    """
    properties = {}
    required = []
    
    for param in parameters:
        param_name = param.get('name')
        param_type = param.get('type')
        param_description = param.get('description', '')
        
        if param_type == "array":
            # Default to array of strings if not specified otherwise
            properties[param_name] = {
                "type": "array",
                "description": param_description,
                "items": {"type": "string"}
            }
        else:
            properties[param_name] = {
                "type": param_type,
                "description": param_description
            }
        
        # Assume all parameters are required
        required.append(param_name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def extract_tool_calls(llm_response) -> list:
    """
    Extract tool calls from LLM response (dict or object).
    Always returns a list of dicts.
    """
    tool_calls = getattr(llm_response, "tool_calls", None)
    if tool_calls is None and isinstance(llm_response, dict):
        tool_calls = llm_response.get("tool_calls")
    if not tool_calls:
        return []
    # Convert each tool_call to dict if not already
    normalized = []
    for call in tool_calls:
        if isinstance(call, dict):
            normalized.append(call)
        elif hasattr(call, "to_dict"):
            normalized.append(call.to_dict())
        elif hasattr(call, "__dict__"):
            normalized.append(vars(call))
        else:
            normalized.append(call)
    return normalized