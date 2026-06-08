from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    
    notify_type = Column(String(20), nullable=False)
    notify_when = Column(String(20), nullable=False, default="on_failure")
    
    webhook_url = Column(String(500), nullable=True)
    secret_key = Column(String(200), nullable=True)
    at_mobiles = Column(JSON, default=list)
    at_all = Column(Boolean, default=False)
    
    assignees = Column(JSON, default=list)
    
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project")


class NotificationRecord(Base):
    __tablename__ = "notification_records"

    id = Column(Integer, primary_key=True, index=True)
    notification_config_id = Column(Integer, ForeignKey("notification_configs.id"), nullable=True)
    execution_record_id = Column(Integer, ForeignKey("execution_records.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    notify_type = Column(String(20), nullable=False)
    
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    
    assignees = Column(JSON, default=list)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notification_config = relationship("NotificationConfig")
    execution_record = relationship("ExecutionRecord")
    project = relationship("Project")
