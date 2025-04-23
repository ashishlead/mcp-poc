import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import importlib
import inspect

import litellm
from langfuse import Langfuse
from langfuse.client import AsyncClient

from agent_runner.db.models import Run as DBRun, RunStep as DBRunStep, Chat as DBChat, RunFunctionCall as DBRunFunctionCall
from sqlalchemy.orm import Session


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
            self.db_run = DBRun(
                workspace_id=self.workspace.db_workspace.id,
                started_at=datetime.utcnow(),
                status="running",
                input_kwargs=self.kwargs,
                results={}
            )
            self.db.add(self.db_run)
            self.db.commit()
            self.db.refresh(self.db_run)
        
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
            self.db_run.ended_at = datetime.utcnow()
            self.db_run.status = "completed"
            self.db_run.results = self.results
            self.db_run.total_time_taken_ms = int((time.time() - start_time) * 1000)
            self.db.commit()
        
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
            self.current_db_step = DBRunStep(
                run_id=self.db_run.id,
                step_name=step_id,
                started_at=datetime.utcnow(),
                status="running"
            )
            self.db.add(self.current_db_step)
            self.db.commit()
            self.db.refresh(self.current_db_step)
        
        # Create Langfuse span for this step
        step_span = self.trace.span(
            name=f"Step: {step_id}",
            metadata={
                "step_details": step_details
            }
        )
        
        try:
            # Prepare conversation
            conversation = []
            if step_details.get('passConversationToNextStep', False) and self.conversation_history:
                conversation = self.conversation_history.copy()
            else:
                conversation = step_details.get('chat', [])
            
            # Build tools array
            tools = []
            if 'function' in step_details:
                for func_item in step_details['function']:
                    func_name = func_item.get('name') if isinstance(func_item, dict) else func_item
                    func_details = self.workspace.data.function_details.get(func_name, {})
                    
                    if func_details:
                        tool = {
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "description": func_details.get('description', ''),
                                "parameters": self._convert_parameters_to_schema(func_details.get('parameters', []))
                            }
                        }
                        tools.append(tool)
            
            # Call LLM
            llm_span = step_span.span(name="LLM Call")
            model = step_details.get('model', 'gpt-4')
            
            response = await litellm.acompletion(
                model=model,
                messages=conversation,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                metadata={
                    "langfuse": {
                        "trace_id": self.trace.id,
                        "span_id": llm_span.id
                    }
                }
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
                db_chat = DBChat(
                    run_step_id=self.current_db_step.id,
                    conversation=conversation,
                    response=response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    status="completed",
                    tokens_consumed=response.get("usage", {}).get("total_tokens", 0)
                )
                self.db.add(db_chat)
                self.db.commit()
            
            # Get LLM response
            llm_response = response.get("choices", [{}])[0].get("message", {})
            
            # Append response to history
            self.conversation_history.append({"role": "assistant", "content": llm_response.get("content", "")})
            
            # Check for tool calls
            if "tool_calls" in llm_response and llm_response["tool_calls"]:
                tool_calls = llm_response["tool_calls"]
                
                # Process tool calls
                if step_details.get('runFunctionsInParallel', False):
                    # Run functions in parallel
                    tasks = []
                    for tool_call in tool_calls:
                        function_name = tool_call.get("function", {}).get("name")
                        function_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                        
                        func_details = self.workspace.data.function_details.get(function_name, {})
                        tasks.append(self._execute_function(function_name, func_details, function_args, tool_call.get("id")))
                    
                    await asyncio.gather(*tasks)
                else:
                    # Run functions sequentially
                    for tool_call in tool_calls:
                        function_name = tool_call.get("function", {}).get("name")
                        function_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                        
                        func_details = self.workspace.data.function_details.get(function_name, {})
                        await self._execute_function(function_name, func_details, function_args, tool_call.get("id"))
            
            # Update step record in DB
            if self.current_db_step:
                self.current_db_step.ended_at = datetime.utcnow()
                self.current_db_step.status = "completed"
                self.current_db_step.time_taken_ms = int((time.time() - step_start_time) * 1000)
                self.db.commit()
            
            # End the step span
            step_span.end()
            
        except Exception as e:
            # Handle error
            if self.current_db_step:
                self.current_db_step.ended_at = datetime.utcnow()
                self.current_db_step.status = "failed"
                self.current_db_step.time_taken_ms = int((time.time() - step_start_time) * 1000)
                self.db.commit()
            
            step_span.end(status="error", statusMessage=str(e))
            raise
    
    async def _execute_function(self, func_name: str, func_details: Dict, args: Dict, tool_call_id: str = None):
        """Execute a function"""
        function_start_time = time.time()
        
        # Create function call record in DB
        db_function_call = None
        if self.current_db_step:
            db_function_call = DBRunFunctionCall(
                run_step_id=self.current_db_step.id,
                function_name=func_name,
                args=args,
                started_at=datetime.utcnow(),
                status="running"
            )
            self.db.add(db_function_call)
            self.db.commit()
            self.db.refresh(db_function_call)
        
        # Create Langfuse span for this function call
        function_span = self.trace.span(
            name=f"Function: {func_name}",
            input=args,
            metadata={
                "function_details": func_details
            }
        )
        
        try:
            # Execute the function
            # First, try to find the function in the global namespace
            if func_name in globals():
                function = globals()[func_name]
            else:
                # Try to import the function from a module
                # This assumes functions are defined in a module structure like agent_runner.functions.func_name
                try:
                    module = importlib.import_module(f"agent_runner.functions.{func_name}")
                    function = getattr(module, func_name)
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
            
            # Check if the function is async
            is_async = inspect.iscoroutinefunction(function)
            
            # Call the function
            if is_async:
                result = await function(**args)
            else:
                result = function(**args)
            
            # Store the result
            self.results[func_name] = result
            
            # Update function call record in DB
            if db_function_call:
                db_function_call.ended_at = datetime.utcnow()
                db_function_call.status = "completed"
                db_function_call.result = str(result)
                self.db.commit()
            
            # End the function span
            function_span.end(
                output=result,
                metadata={
                    "execution_time_ms": int((time.time() - function_start_time) * 1000)
                }
            )
            
            # Append tool result to conversation history
            if tool_call_id:
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func_name,
                    "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                })
            
            return result
            
        except Exception as e:
            # Handle error
            if db_function_call:
                db_function_call.ended_at = datetime.utcnow()
                db_function_call.status = "failed"
                db_function_call.result = str(e)
                self.db.commit()
            
            function_span.end(status="error", statusMessage=str(e))
            raise
    
    def _convert_parameters_to_schema(self, parameters: List[Dict]) -> Dict:
        """Convert parameters list to JSON Schema"""
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
