import json
import time
from typing import Dict, List, Any, Optional
import litellm

from langfuse import Langfuse
from langfuse.client import AsyncClient


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


def extract_tool_calls(llm_response: Dict) -> List[Dict]:
    """Extract tool calls from LLM response
    
    Args:
        llm_response: The LLM response message
        
    Returns:
        List of tool call objects
    """
    if "tool_calls" in llm_response and llm_response["tool_calls"]:
        return llm_response["tool_calls"]
    return []
