import json
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

from agent_runner.core.run import Run
from agent_runner.db.models import Workspace as DBWorkspace, WorkspaceFunction, WorkspaceStep, WorkspaceStepFunction
from sqlalchemy.orm import Session


class WorkspaceData:
    def __init__(self, functions: List[str], steps: List[Dict], step_details: Dict[str, Dict], function_details: Dict[str, Dict]):
        self.functions = functions
        self.steps = steps
        self.step_details = step_details
        self.function_details = function_details


class Workspace:
    def __init__(self, data: WorkspaceData, db_workspace: Optional[DBWorkspace] = None):
        self.data = data
        self.db_workspace = db_workspace
    
    async def run(self, **kwargs) -> Run:
        """Create and execute a run for this workspace"""
        run = Run(workspace=self, kwargs=kwargs)
        await run.execute()
        return run


class WorkspaceManager:
    def __init__(self, db: Session):
        self.db = db
    
    def load(self, workspace_json: Dict) -> Workspace:
        """Load a workspace from JSON data"""
        # Extract functions and steps
        functions = []
        steps = []
        step_details = {}
        function_details = {}
        
        # Parse the workspace JSON
        for key, value in workspace_json.items():
            if key.endswith('#details'):
                if '@func-' in key:
                    # This is a function detail
                    func_name = key.split('@func-')[1].split('#')[0]
                    function_details[func_name] = value
                elif '@step-' in key:
                    # This is a step detail
                    step_name = key.split('@step-')[1].split('#')[0]
                    step_details[step_name] = value
                elif '#details' in key and not ('@func-' in key or '@step-' in key):
                    # This is the workspace details
                    if 'steps' in value:
                        steps = value['steps']
                    if 'functions' in value:
                        functions = value['functions']
        
        # Create WorkspaceData
        workspace_data = WorkspaceData(
            functions=functions,
            steps=steps,
            step_details=step_details,
            function_details=function_details
        )
        
        return Workspace(data=workspace_data)
    
    def create_workspace(self, name: str, version: str, json_data: Dict) -> Workspace:
        """Create a new workspace in the database"""
        db_workspace = DBWorkspace(
            name=name,
            version=version,
            json_data=json_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(db_workspace)
        self.db.commit()
        self.db.refresh(db_workspace)
        
        # Extract and create functions and steps
        workspace = self.load(json_data)
        
        # Save functions
        for func_name, func_details in workspace.data.function_details.items():
            db_function = WorkspaceFunction(
                workspace_id=db_workspace.id,
                name=func_name,
                description=func_details.get('description', ''),
                parameters=func_details.get('parameters', []),
                code=func_details.get('code', '')
            )
            self.db.add(db_function)
        
        self.db.commit()
        
        # Save steps
        for step in workspace.data.steps:
            step_id = step.get('id')
            step_detail = workspace.data.step_details.get(step_id, {})
            
            db_step = WorkspaceStep(
                workspace_id=db_workspace.id,
                name=step_id,
                chat=step_detail.get('chat', []),
                next_step=step_detail.get('nextStep', '-'),
                model=step_detail.get('model', 'gpt-4'),
                run_functions_in_parallel=step_detail.get('runFunctionsInParallel', False),
                pass_conversation_to_next_step=step_detail.get('passConversationToNextStep', False)
            )
            self.db.add(db_step)
            self.db.commit()
            self.db.refresh(db_step)
            
            # Link step to functions
            if 'function' in step_detail:
                for func_item in step_detail['function']:
                    func_name = func_item.get('name') if isinstance(func_item, dict) else func_item
                    
                    # Find the function in the database
                    db_function = self.db.query(WorkspaceFunction).filter_by(
                        workspace_id=db_workspace.id,
                        name=func_name
                    ).first()
                    
                    if db_function:
                        db_step_function = WorkspaceStepFunction(
                            workspace_step_id=db_step.id,
                            workspace_function_id=db_function.id
                        )
                        self.db.add(db_step_function)
        
        self.db.commit()
        
        # Return the workspace with DB reference
        workspace.db_workspace = db_workspace
        return workspace
    
    def update_workspace(self, workspace_id: int, name: str, version: str, json_data: Dict) -> Workspace:
        """Update an existing workspace"""
        db_workspace = self.db.query(DBWorkspace).filter_by(id=workspace_id).first()
        
        if not db_workspace:
            raise ValueError(f"Workspace with ID {workspace_id} not found")
        
        # Update workspace
        db_workspace.name = name
        db_workspace.version = version
        db_workspace.json_data = json_data
        db_workspace.updated_at = datetime.utcnow()
        
        # Delete existing functions and steps
        self.db.query(WorkspaceStepFunction).filter(
            WorkspaceStepFunction.workspace_step_id.in_(
                self.db.query(WorkspaceStep.id).filter_by(workspace_id=workspace_id)
            )
        ).delete(synchronize_session=False)
        
        self.db.query(WorkspaceFunction).filter_by(workspace_id=workspace_id).delete(synchronize_session=False)
        self.db.query(WorkspaceStep).filter_by(workspace_id=workspace_id).delete(synchronize_session=False)
        
        self.db.commit()
        
        # Extract and create functions and steps
        workspace = self.load(json_data)
        
        # Save functions
        for func_name, func_details in workspace.data.function_details.items():
            db_function = WorkspaceFunction(
                workspace_id=db_workspace.id,
                name=func_name,
                description=func_details.get('description', ''),
                parameters=func_details.get('parameters', []),
                code=func_details.get('code', '')
            )
            self.db.add(db_function)
        
        self.db.commit()
        
        # Save steps
        for step in workspace.data.steps:
            step_id = step.get('id')
            step_detail = workspace.data.step_details.get(step_id, {})
            
            db_step = WorkspaceStep(
                workspace_id=db_workspace.id,
                name=step_id,
                chat=step_detail.get('chat', []),
                next_step=step_detail.get('nextStep', '-'),
                model=step_detail.get('model', 'gpt-4'),
                run_functions_in_parallel=step_detail.get('runFunctionsInParallel', False),
                pass_conversation_to_next_step=step_detail.get('passConversationToNextStep', False)
            )
            self.db.add(db_step)
            self.db.commit()
            self.db.refresh(db_step)
            
            # Link step to functions
            if 'function' in step_detail:
                for func_item in step_detail['function']:
                    func_name = func_item.get('name') if isinstance(func_item, dict) else func_item
                    
                    # Find the function in the database
                    db_function = self.db.query(WorkspaceFunction).filter_by(
                        workspace_id=db_workspace.id,
                        name=func_name
                    ).first()
                    
                    if db_function:
                        db_step_function = WorkspaceStepFunction(
                            workspace_step_id=db_step.id,
                            workspace_function_id=db_function.id
                        )
                        self.db.add(db_step_function)
        
        self.db.commit()
        
        # Return the workspace with DB reference
        workspace.db_workspace = db_workspace
        return workspace
    
    def delete_workspace(self, workspace_id: int) -> bool:
        """Delete a workspace"""
        db_workspace = self.db.query(DBWorkspace).filter_by(id=workspace_id).first()
        
        if not db_workspace:
            raise ValueError(f"Workspace with ID {workspace_id} not found")
        
        # Delete related records
        self.db.query(WorkspaceStepFunction).filter(
            WorkspaceStepFunction.workspace_step_id.in_(
                self.db.query(WorkspaceStep.id).filter_by(workspace_id=workspace_id)
            )
        ).delete(synchronize_session=False)
        
        self.db.query(WorkspaceFunction).filter_by(workspace_id=workspace_id).delete(synchronize_session=False)
        self.db.query(WorkspaceStep).filter_by(workspace_id=workspace_id).delete(synchronize_session=False)
        
        # Delete the workspace
        self.db.delete(db_workspace)
        self.db.commit()
        
        return True
    
    def get_workspace(self, workspace_id: int) -> Workspace:
        """Get a workspace by ID"""
        db_workspace = self.db.query(DBWorkspace).filter_by(id=workspace_id).first()
        
        if not db_workspace:
            raise ValueError(f"Workspace with ID {workspace_id} not found")
        
        # Load the workspace
        workspace = self.load(db_workspace.json_data)
        workspace.db_workspace = db_workspace
        
        return workspace
