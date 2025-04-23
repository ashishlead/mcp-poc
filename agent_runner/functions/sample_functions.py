import json
import asyncio
from typing import Dict, List, Any, Optional


async def fetch_data(url: str, headers: Optional[Dict] = None) -> Dict:
    """Fetch data from a URL
    
    Args:
        url: The URL to fetch data from
        headers: Optional headers to include in the request
        
    Returns:
        The response data as a dictionary
    """
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Failed to fetch data: {response.status}"}
    except Exception as e:
        return {"error": str(e)}


def calculate_statistics(data: List[Dict], field: str) -> Dict:
    """Calculate basic statistics for a field in a list of dictionaries
    
    Args:
        data: List of dictionaries containing the field
        field: The field to calculate statistics for
        
    Returns:
        Dictionary with statistics (min, max, avg, sum, count)
    """
    if not data:
        return {"error": "No data provided"}
    
    try:
        values = [item.get(field, 0) for item in data if field in item]
        
        if not values:
            return {"error": f"Field '{field}' not found in data"}
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values),
            "count": len(values)
        }
    except Exception as e:
        return {"error": str(e)}


async def send_notification(recipient: str, message: str, channel: str = "email") -> Dict:
    """Send a notification to a recipient
    
    Args:
        recipient: The recipient of the notification
        message: The message to send
        channel: The channel to use (email, sms, slack)
        
    Returns:
        Status of the notification
    """
    # This is a mock implementation
    # In a real application, you would integrate with actual notification services
    
    # Simulate async operation
    await asyncio.sleep(1)
    
    return {
        "status": "sent",
        "recipient": recipient,
        "channel": channel,
        "timestamp": "2023-04-23T12:34:56Z"
    }


def process_text(text: str, operations: List[str]) -> Dict:
    """Process text with various operations
    
    Args:
        text: The text to process
        operations: List of operations to perform (lowercase, uppercase, tokenize, count_words)
        
    Returns:
        The processed text
    """
    results = {}
    
    for operation in operations:
        if operation == "lowercase":
            results["lowercase"] = text.lower()
        elif operation == "uppercase":
            results["uppercase"] = text.upper()
        elif operation == "tokenize":
            results["tokenize"] = text.split()
        elif operation == "count_words":
            results["count_words"] = len(text.split())
        elif operation == "count_chars":
            results["count_chars"] = len(text)
    
    return results
