from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=True)
    
    task_type = Column(String(20), nullable=False, default="single")
    cron_expression = Column(String(100), nullable=True)
    
    test_suite_ids = Column(JSON, default=list)
    test_case_ids = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    
    retry_count = Column(Integer, default=0)
    retry_interval = Column(Integer, default=5)
    run_parallel = Column(Boolean, default=False)
    
    is_enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project")
    environment = relationship("Environment")
    execution_records = relationship("ExecutionRecord", back_populates="task", cascade="all, delete-orphan")
