from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ExecutionRecord(Base):
    __tablename__ = "execution_records"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    
    trigger_type = Column(String(20), nullable=False, default="manual")
    status = Column(String(20), nullable=False, default="running")
    
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    skipped_cases = Column(Integer, default=0)
    pass_rate = Column(Float, default=0.0)
    
    total_duration = Column(Float, default=0.0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    retry_attempt = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="execution_records")
    project = relationship("Project")
    environment = relationship("Environment")
    case_results = relationship("CaseResult", back_populates="execution_record", cascade="all, delete-orphan")


class CaseResult(Base):
    __tablename__ = "case_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_record_id = Column(Integer, ForeignKey("execution_records.id"), nullable=False)
    test_case_id = Column(Integer, nullable=False)
    test_case_name = Column(String(200), nullable=False)
    
    status = Column(String(20), nullable=False)
    duration = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    execution_record = relationship("ExecutionRecord", back_populates="case_results")
    step_results = relationship("StepResult", back_populates="case_result", cascade="all, delete-orphan")


class StepResult(Base):
    __tablename__ = "step_results"

    id = Column(Integer, primary_key=True, index=True)
    case_result_id = Column(Integer, ForeignKey("case_results.id"), nullable=False)
    request_step_id = Column(Integer, nullable=False)
    request_step_name = Column(String(200), nullable=False)
    
    status = Column(String(20), nullable=False)
    duration = Column(Float, default=0.0)
    
    request_url = Column(String(1000), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_headers = Column(JSON, default=dict)
    request_body = Column(Text, nullable=True)
    
    response_status = Column(Integer, nullable=True)
    response_headers = Column(JSON, default=dict)
    response_body = Column(Text, nullable=True)
    response_body_summary = Column(Text, nullable=True)
    
    error_message = Column(Text, nullable=True)
    assertion_results = Column(JSON, default=list)
    extracted_variables = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case_result = relationship("CaseResult", back_populates="step_results")
