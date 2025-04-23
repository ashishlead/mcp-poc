from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Workspace(Base):
    __tablename__ = 'workspaces'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    json_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    functions = relationship('WorkspaceFunction', back_populates='workspace')
    steps = relationship('WorkspaceStep', back_populates='workspace')
    runs = relationship('Run', back_populates='workspace')

class WorkspaceFunction(Base):
    __tablename__ = 'workspace_functions'
    
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id'))
    name = Column(String, nullable=False)
    description = Column(String)
    parameters = Column(JSON)
    code = Column(Text)
    
    workspace = relationship('Workspace', back_populates='functions')
    step_functions = relationship('WorkspaceStepFunction', back_populates='function')

class WorkspaceStep(Base):
    __tablename__ = 'workspace_steps'
    
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id'))
    name = Column(String, nullable=False)
    chat = Column(JSON)
    next_step = Column(String)
    model = Column(String)
    run_functions_in_parallel = Column(Boolean, default=False)
    pass_conversation_to_next_step = Column(Boolean, default=False)
    
    workspace = relationship('Workspace', back_populates='steps')
    step_functions = relationship('WorkspaceStepFunction', back_populates='step')

class WorkspaceStepFunction(Base):
    __tablename__ = 'workspace_step_functions'
    
    id = Column(Integer, primary_key=True)
    workspace_step_id = Column(Integer, ForeignKey('workspace_steps.id'))
    workspace_function_id = Column(Integer, ForeignKey('workspace_functions.id'))
    
    step = relationship('WorkspaceStep', back_populates='step_functions')
    function = relationship('WorkspaceFunction', back_populates='step_functions')

class Run(Base):
    __tablename__ = 'runs'
    
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id'))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    status = Column(String)
    total_tokens_consumed = Column(Integer, default=0)
    total_time_taken_ms = Column(Integer, default=0)
    input_kwargs = Column(JSON)
    results = Column(JSON)
    
    workspace = relationship('Workspace', back_populates='runs')
    steps = relationship('RunStep', back_populates='run')

class RunStep(Base):
    __tablename__ = 'run_steps'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    step_name = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    status = Column(String)
    time_taken_ms = Column(Integer, default=0)
    
    run = relationship('Run', back_populates='steps')
    chats = relationship('Chat', back_populates='run_step')
    function_calls = relationship('RunFunctionCall', back_populates='run_step')

class Chat(Base):
    __tablename__ = 'chat'
    
    id = Column(Integer, primary_key=True)
    run_step_id = Column(Integer, ForeignKey('run_steps.id'))
    conversation = Column(JSON)
    response = Column(String)
    status = Column(String)
    tokens_consumed = Column(Integer, default=0)
    
    run_step = relationship('RunStep', back_populates='chats')

class RunFunctionCall(Base):
    __tablename__ = 'run_function_calls'
    
    id = Column(Integer, primary_key=True)
    run_step_id = Column(Integer, ForeignKey('run_steps.id'))
    function_name = Column(String, nullable=False)
    args = Column(JSON)
    result = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    status = Column(String)
    
    run_step = relationship('RunStep', back_populates='function_calls')


def init_db(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
