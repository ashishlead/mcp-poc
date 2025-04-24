import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from langfuse import Langfuse
from sqlalchemy.orm import Session

from agent_runner.db.models import Run as DBRun, RunStep as DBRunStep, Chat as DBChat, RunFunctionCall as DBRunFunctionCall
from agent_runner.core.llm.client import call_llm, build_tools_array, extract_tool_calls
from agent_runner.core.llm.conversation import prepare_conversation, append_assistant_response, append_tool_result
from agent_runner.core.function_execution.executor import execute_function, execute_functions_parallel, execute_functions_sequential
from agent_runner.core.db_operations.run_operations import (
    create_run_record, update_run_record, 
    create_step_record, update_step_record,
    create_chat_record
)


class Run:
    def __init__(self, workspace, kwargs: Dict, db: Optional[Session] = None):
        self.workspace = workspace
        self.kwargs = kwargs
        self.conversation_history = []
        self.results = {}
        self.db = db
        self.db_run = None
        self.current_step = None
        self.current_db_step = None
        
        # Initialize Langfuse
        self.langfuse = Langfuse()
        self.trace = self.langfuse.trace(
            name=f"Workspace: {workspace.db_workspace.name if workspace.db_workspace else 'Unnamed'}",
            metadata={
                "workspace_id": workspace.db_workspace.id if workspace.db_workspace else None,
                "input_kwargs": kwargs
            }
        )
    
    async def execute(self):
        """Execute the run"""
        start_time = time.time()
        
        # Create run record in DB if we have a db connection
        if self.db and self.workspace.db_workspace:
            self.db_run = create_run_record(self.db, self.workspace.db_workspace.id, self.kwargs)
        
        # Get the first step
        if not self.workspace.data.steps:
            raise ValueError("No steps defined in workspace")
        
        first_step = self.workspace.data.steps[0]
        current_step = first_step.get('id')
        
        # Execute steps until we reach the end
        while current_step != "-":
            self.current_step = current_step
            await self._execute_step(current_step)
            
            # Get the next step
            step_details = self.workspace.data.step_details.get(current_step, {})
            current_step = step_details.get('nextStep', '-')
        
        # Update run record in DB
        if self.db_run:
            update_run_record(
                self.db, 
                self.db_run, 
                "completed", 
                self.results, 
                int((time.time() - start_time) * 1000)
            )
        
        # Complete the Langfuse trace
        self.trace.update(status="success")
        self.trace.end()
        
        return self.results
    
    async def _execute_step(self, step_id: str):
        """Execute a single step"""
        step_start_time = time.time()
        step_details = self.workspace.data.step_details.get(step_id, {})
        
        # Create step record in DB
        if self.db_run:
            self.current_db_step = create_step_record(self.db, self.db_run.id, step_id)
        
        # Create Langfuse span for this step
        step_span = self.trace.span(
            name=f"Step: {step_id}",
            metadata={
                "step_details": step_details
            }
        )
        
        try:
            # Prepare conversation
            conversation = prepare_conversation(step_details, self.conversation_history)
            
            # Build tools array
            available_functions = []
            if 'function' in step_details:
                for func_item in step_details['function']:
                    if isinstance(func_item, dict):
                        available_functions.append(func_item.get('name'))
                    else:
                        available_functions.append(func_item)
            
            tools = build_tools_array(self.workspace.data.function_details, available_functions)
            
            # Call LLM recursively to handle tool calls
            await self._call_llm_with_tools(conversation, tools, step_details, step_span)
            
            # Update step record in DB
            if self.current_db_step:
                update_step_record(
                    self.db, 
                    self.current_db_step, 
                    "completed", 
                    int((time.time() - step_start_time) * 1000)
                )
            
            # End the step span
            step_span.end()
            
        except Exception as e:
            # Handle error
            if self.current_db_step:
                update_step_record(
                    self.db, 
                    self.current_db_step, 
                    "failed", 
                    int((time.time() - step_start_time) * 1000)
                )
            
            step_span.end(status="error", statusMessage=str(e))
            raise
    
    async def _call_llm_with_tools(self, conversation, tools, step_details, parent_span, max_iterations=5):
        """Call LLM with tools and handle recursive tool calls"""
        iteration = 0
        run_in_parallel = step_details.get('runFunctionsInParallel', False)
        model = step_details.get('model', 'gpt-4')
        
        while iteration < max_iterations:
            iteration += 1
            
            # Create a span for this LLM call iteration
            llm_span = parent_span.span(name=f"LLM Call (Iteration {iteration})")
            
            # Call LLM
            response = await call_llm(
                model=model,
                messages=conversation,
                tools=tools,
                trace_id=self.trace.id,
                span_id=llm_span.id
            )
            
            # Update LLM span with response
            llm_span.end(
                output=response,
                metadata={
                    "model": model,
                    "tokens": {
                        "prompt": response.get("usage", {}).get("prompt_tokens", 0),
                        "completion": response.get("usage", {}).get("completion_tokens", 0),
                        "total": response.get("usage", {}).get("total_tokens", 0)
                    }
                }
            )
            
            # Create chat record in DB
            if self.current_db_step:
                create_chat_record(
                    self.db,
                    self.current_db_step.id,
                    conversation,
                    response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    response.get("usage", {}).get("total_tokens", 0)
                )
            
            # Get LLM response
            llm_response = response.get("choices", [{}])[0].get("message", {})
            
            # Append response to history
            append_assistant_response(self.conversation_history, llm_response.get("content", ""))
            
            # Check for tool calls
            tool_calls = extract_tool_calls(llm_response)
            if tool_calls:
                # Process tool calls
                if run_in_parallel:
                    # Run functions in parallel
                    async for call_id, function_name, result in execute_functions_parallel(
                        tool_calls, 
                        self.workspace.data.function_details,
                        self.trace,
                        self.db,
                        self.current_db_step
                    ):
                        # Store the result
                        self.results[function_name] = result
                        
                        # Append tool result to conversation
                        append_tool_result(self.conversation_history, call_id, function_name, result)
                else:
                    # Run functions sequentially
                    async for call_id, function_name, result in execute_functions_sequential(
                        tool_calls, 
                        self.workspace.data.function_details,
                        self.trace,
                        self.db,
                        self.current_db_step
                    ):
                        # Store the result
                        self.results[function_name] = result
                        
                        # Append tool result to conversation
                        append_tool_result(self.conversation_history, call_id, function_name, result)
                
                # Continue the loop to make another LLM call with the tool results
                continue
            else:
                # No tool calls, we're done
                break
        
        # If we've reached the maximum number of iterations, log a warning
        if iteration >= max_iterations:
            print(f"Warning: Reached maximum number of iterations ({max_iterations}) for step {self.current_step}")
