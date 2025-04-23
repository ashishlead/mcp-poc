from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class WorkspaceBase(BaseModel):
    name: str
    version: str
    json_data: Dict[str, Any]

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class RunCreate(BaseModel):
    workspace_id: int
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)

class RunResponse(BaseModel):
    id: int
    workspace_id: int
    started_at: str
    ended_at: Optional[str] = None
    status: str
    total_tokens_consumed: int
    total_time_taken_ms: int
    input_kwargs: Dict[str, Any]
    results: Dict[str, Any]

    class Config:
        from_attributes = True
