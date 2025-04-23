from datetime import datetime
from typing import Dict, List, Any, Optional

from agent_runner.db.models import Run as DBRun, RunStep as DBRunStep, Chat as DBChat, RunFunctionCall as DBRunFunctionCall


def create_run_record(db, workspace_id: int, kwargs: Dict) -> DBRun:
    """Create a new run record in the database
    
    Args:
        db: Database session
        workspace_id: ID of the workspace
        kwargs: Input arguments for the run
        
    Returns:
        The created run record
    """
    db_run = DBRun(
        workspace_id=workspace_id,
        started_at=datetime.utcnow(),
        status="running",
        input_kwargs=kwargs,
        results={}
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    return db_run


def update_run_record(db, db_run: DBRun, status: str, results: Dict, total_time_ms: int) -> DBRun:
    """Update a run record in the database
    
    Args:
        db: Database session
        db_run: Run record to update
        status: New status
        results: Results of the run
        total_time_ms: Total time taken in milliseconds
        
    Returns:
        The updated run record
    """
    db_run.ended_at = datetime.utcnow()
    db_run.status = status
    db_run.results = results
    db_run.total_time_taken_ms = total_time_ms
    db.commit()
    
    return db_run


def create_step_record(db, run_id: int, step_name: str) -> DBRunStep:
    """Create a new step record in the database
    
    Args:
        db: Database session
        run_id: ID of the run
        step_name: Name of the step
        
    Returns:
        The created step record
    """
    db_step = DBRunStep(
        run_id=run_id,
        step_name=step_name,
        started_at=datetime.utcnow(),
        status="running"
    )
    db.add(db_step)
    db.commit()
    db.refresh(db_step)
    
    return db_step


def update_step_record(db, db_step: DBRunStep, status: str, time_taken_ms: int) -> DBRunStep:
    """Update a step record in the database
    
    Args:
        db: Database session
        db_step: Step record to update
        status: New status
        time_taken_ms: Time taken in milliseconds
        
    Returns:
        The updated step record
    """
    db_step.ended_at = datetime.utcnow()
    db_step.status = status
    db_step.time_taken_ms = time_taken_ms
    db.commit()
    
    return db_step


def create_chat_record(db, run_step_id: int, conversation: List[Dict], response: str, tokens: int) -> DBChat:
    """Create a new chat record in the database
    
    Args:
        db: Database session
        run_step_id: ID of the run step
        conversation: Conversation history
        response: LLM response
        tokens: Tokens consumed
        
    Returns:
        The created chat record
    """
    db_chat = DBChat(
        run_step_id=run_step_id,
        conversation=conversation,
        response=response,
        status="completed",
        tokens_consumed=tokens
    )
    db.add(db_chat)
    db.commit()
    
    return db_chat


def create_function_call_record(db, run_step_id: int, function_name: str, args: Dict) -> DBRunFunctionCall:
    """Create a new function call record in the database
    
    Args:
        db: Database session
        run_step_id: ID of the run step
        function_name: Name of the function
        args: Arguments for the function
        
    Returns:
        The created function call record
    """
    db_function_call = DBRunFunctionCall(
        run_step_id=run_step_id,
        function_name=function_name,
        args=args,
        started_at=datetime.utcnow(),
        status="running"
    )
    db.add(db_function_call)
    db.commit()
    db.refresh(db_function_call)
    
    return db_function_call


def update_function_call_record(db, db_function_call: DBRunFunctionCall, status: str, result: Any) -> DBRunFunctionCall:
    """Update a function call record in the database
    
    Args:
        db: Database session
        db_function_call: Function call record to update
        status: New status
        result: Result of the function call
        
    Returns:
        The updated function call record
    """
    db_function_call.ended_at = datetime.utcnow()
    db_function_call.status = status
    db_function_call.result = str(result)
    db.commit()
    
    return db_function_call
