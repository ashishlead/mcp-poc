from typing import Dict, List, Any, Optional


def prepare_conversation(step_details: Dict, conversation_history: Optional[List[Dict]] = None) -> List[Dict]:
    """Prepare the conversation for an LLM call
    
    Args:
        step_details: Details of the current step
        conversation_history: Optional previous conversation history
        
    Returns:
        The prepared conversation messages
    """
    if step_details.get('passConversationToNextStep', False) and conversation_history:
        return conversation_history.copy()
    else:
        return step_details.get('chat', [])


def append_assistant_response(conversation: List[Dict], content: str) -> List[Dict]:
    """Append an assistant response to the conversation
    
    Args:
        conversation: The current conversation
        content: The content of the assistant's response
        
    Returns:
        The updated conversation
    """
    conversation.append({"role": "assistant", "content": content})
    return conversation


def append_tool_result(conversation: List[Dict], tool_call_id: str, function_name: str, result: Any) -> List[Dict]:
    """Append a tool result to the conversation
    
    Args:
        conversation: The current conversation
        tool_call_id: ID of the tool call
        function_name: Name of the function
        result: Result of the function call
        
    Returns:
        The updated conversation
    """
    import json
    
    # Format the result
    if isinstance(result, (dict, list)):
        result_str = json.dumps(result)
    else:
        result_str = str(result)
    
    conversation.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": function_name,
        "content": result_str
    })
    
    return conversation


def get_conversation_tokens(conversation: List[Dict]) -> int:
    """Estimate the number of tokens in a conversation
    
    This is a very rough estimate and should be replaced with a proper tokenizer.
    
    Args:
        conversation: The conversation to estimate tokens for
        
    Returns:
        Estimated number of tokens
    """
    import json
    
    # Very rough estimate: 1 token ~= 4 characters
    total_chars = 0
    
    for message in conversation:
        # Add characters for the role
        total_chars += len(message.get("role", ""))
        
        # Add characters for the content
        content = message.get("content", "")
        if content:
            total_chars += len(content)
        
        # Add characters for tool calls if present
        if "tool_calls" in message:
            tool_calls_str = json.dumps(message["tool_calls"])
            total_chars += len(tool_calls_str)
    
    # Rough estimate: 1 token ~= 4 characters
    return total_chars // 4
