from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import asyncio

from agent_runner.api.models import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, 
    RunCreate, RunResponse
)
from agent_runner.db.database import get_db
from agent_runner.db.models import Workspace as DBWorkspace, Run as DBRun
from agent_runner.core.workspace import WorkspaceManager

router = APIRouter()

@router.post("/workspaces/", response_model=WorkspaceResponse)
def create_workspace(workspace: WorkspaceCreate, db: Session = Depends(get_db)):
    """Create a new workspace"""
    manager = WorkspaceManager(db)
    
    try:
        workspace_obj = manager.create_workspace(
            name=workspace.name,
            version=workspace.version,
            json_data=workspace.json_data
        )
        
        return workspace_obj.db_workspace
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)):
    """Get a workspace by ID"""
    workspace = db.query(DBWorkspace).filter(DBWorkspace.id == workspace_id).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return workspace

@router.get("/workspaces/", response_model=List[WorkspaceResponse])
def list_workspaces(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all workspaces"""
    workspaces = db.query(DBWorkspace).offset(skip).limit(limit).all()
    return workspaces

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(workspace_id: int, workspace: WorkspaceUpdate, db: Session = Depends(get_db)):
    """Update a workspace"""
    manager = WorkspaceManager(db)
    
    try:
        workspace_obj = manager.update_workspace(
            workspace_id=workspace_id,
            name=workspace.name,
            version=workspace.version,
            json_data=workspace.json_data
        )
        
        return workspace_obj.db_workspace
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/workspaces/{workspace_id}", response_model=dict)
def delete_workspace(workspace_id: int, db: Session = Depends(get_db)):
    """Delete a workspace"""
    manager = WorkspaceManager(db)
    
    try:
        manager.delete_workspace(workspace_id=workspace_id)
        return {"success": True, "message": f"Workspace {workspace_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def run_workspace_async(workspace_id: int, kwargs: dict, db: Session):
    """Run a workspace asynchronously"""
    manager = WorkspaceManager(db)
    
    try:
        workspace = manager.get_workspace(workspace_id)
        await workspace.run(**kwargs)
    except Exception as e:
        # Log the error
        print(f"Error running workspace {workspace_id}: {e}")

@router.post("/workspaces/{workspace_id}/run", response_model=dict)
def run_workspace(workspace_id: int, run_data: RunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Run a workspace and return the run ID"""
    # Check if workspace exists
    workspace = db.query(DBWorkspace).filter(DBWorkspace.id == workspace_id).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Create a run record
    db_run = DBRun(
        workspace_id=workspace_id,
        status="queued",
        input_kwargs=run_data.kwargs
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    # Start the run in the background
    background_tasks.add_task(run_workspace_async, workspace_id, run_data.kwargs, db)
    
    return {"run_id": db_run.id, "status": "queued"}

@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get a run by ID"""
    run = db.query(DBRun).filter(DBRun.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return run

@router.get("/workspaces/{workspace_id}/runs", response_model=List[RunResponse])
def list_workspace_runs(workspace_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all runs for a workspace"""
    # Check if workspace exists
    workspace = db.query(DBWorkspace).filter(DBWorkspace.id == workspace_id).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    runs = db.query(DBRun).filter(DBRun.workspace_id == workspace_id).offset(skip).limit(limit).all()
    return runs
