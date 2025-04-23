import json
import time
import asyncio
import importlib
import inspect
from typing import Dict, List, Any, Optional
from datetime import datetime

from langfuse import Langfuse


async def execute_function(func_name: str, func_details: Dict, args: Dict, trace=None, db=None, db_step=None):
    """Execute a function with the given arguments
    
    Args:
        func_name: Name of the function to execute
        func_details: Details of the function
        args: Arguments to pass to the function
        trace: Optional Langfuse trace
        db: Optional database session
        db_step: Optional database step record
        
    Returns:
        The result of the function execution
    """
    function_start_time = time.time()
    
    # Create function call record in DB
    db_function_call = None
    if db and db_step:
        from agent_runner.db.models import RunFunctionCall
        db_function_call = RunFunctionCall(
            run_step_id=db_step.id,
            function_name=func_name,
            args=args,
            started_at=datetime.utcnow(),
            status="running"
        )
        db.add(db_function_call)
        db.commit()
        db.refresh(db_function_call)
    
    # Create Langfuse span for this function call
    function_span = None
    if trace:
        function_span = trace.span(
            name=f"Function: {func_name}",
            input=args,
            metadata={
                "function_details": func_details
            }
        )
    
    try:
        # Find and execute the function
        function = find_function(func_name, func_details)
        
        # Check if the function is async
        is_async = inspect.iscoroutinefunction(function)
        
        # Call the function
        if is_async:
            result = await function(**args)
        else:
            result = function(**args)
        
        # Update function call record in DB
        if db_function_call:
            db_function_call.ended_at = datetime.utcnow()
            db_function_call.status = "completed"
            db_function_call.result = str(result)
            db.commit()
        
        # End the function span
        if function_span:
            function_span.end(
                output=result,
                metadata={
                    "execution_time_ms": int((time.time() - function_start_time) * 1000)
                }
            )
        
        return result
        
    except Exception as e:
        # Handle error
        if db_function_call:
            db_function_call.ended_at = datetime.utcnow()
            db_function_call.status = "failed"
            db_function_call.result = str(e)
            db.commit()
        
        if function_span:
            function_span.end(status="error", statusMessage=str(e))
        
        raise


async def execute_functions_parallel(function_calls: List[Dict], function_details: Dict, trace=None, db=None, db_step=None):
    """Execute multiple functions in parallel
    
    Args:
        function_calls: List of function call objects
        function_details: Dictionary of function details
        trace: Optional Langfuse trace
        db: Optional database session
        db_step: Optional database step record
        
    Returns:
        List of results from function executions
    """
    tasks = []
    results = {}
    
    for call in function_calls:
        function_name = call.get("function", {}).get("name")
        function_args = json.loads(call.get("function", {}).get("arguments", "{}"))
        call_id = call.get("id")
        
        func_details = function_details.get(function_name, {})
        task = execute_function(function_name, func_details, function_args, trace, db, db_step)
        tasks.append((call_id, function_name, task))
    
    # Execute all tasks in parallel
    for call_id, function_name, task in tasks:
        try:
            result = await task
            results[function_name] = result
            yield call_id, function_name, result
        except Exception as e:
            yield call_id, function_name, {"error": str(e)}


async def execute_functions_sequential(function_calls: List[Dict], function_details: Dict, trace=None, db=None, db_step=None):
    """Execute multiple functions sequentially
    
    Args:
        function_calls: List of function call objects
        function_details: Dictionary of function details
        trace: Optional Langfuse trace
        db: Optional database session
        db_step: Optional database step record
        
    Returns:
        List of results from function executions
    """
    results = {}
    
    for call in function_calls:
        function_name = call.get("function", {}).get("name")
        function_args = json.loads(call.get("function", {}).get("arguments", "{}"))
        call_id = call.get("id")
        
        func_details = function_details.get(function_name, {})
        
        try:
            result = await execute_function(function_name, func_details, function_args, trace, db, db_step)
            results[function_name] = result
            yield call_id, function_name, result
        except Exception as e:
            yield call_id, function_name, {"error": str(e)}


def find_function(func_name: str, func_details: Dict):
    """Find a function by name
    
    Args:
        func_name: Name of the function to find
        func_details: Details of the function
        
    Returns:
        The function object
    """
    # First, try to find the function in the global namespace
    if func_name in globals():
        return globals()[func_name]
    
    # Try to import the function from a module
    # This assumes functions are defined in a module structure like agent_runner.functions.func_name
    try:
        module = importlib.import_module(f"agent_runner.functions.{func_name}")
        return getattr(module, func_name)
    except (ImportError, AttributeError):
        # If not found, try to evaluate the function code
        function_code = func_details.get('code', '')
        if not function_code:
            raise ValueError(f"Function {func_name} not found and no code provided")
        
        # Create a local namespace
        local_namespace = {}
        
        # Execute the function code in the local namespace
        exec(function_code, globals(), local_namespace)
        
        # Get the function from the local namespace
        function = local_namespace.get(func_name)
        
        if not function:
            raise ValueError(f"Function {func_name} not found in the executed code")
        
        return function
