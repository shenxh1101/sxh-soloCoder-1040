from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RequestStep(Base):
    __tablename__ = "request_steps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    order = Column(Integer, default=0)
    
    method = Column(String(10), nullable=False, default="GET")
    url = Column(String(500), nullable=False)
    headers = Column(JSON, default=dict)
    params = Column(JSON, default=dict)
    body = Column(Text, nullable=True)
    body_type = Column(String(20), default="json")
    
    extract_variables = Column(JSON, default=dict)
    skip_on_failure = Column(Boolean, default=False)
    timeout = Column(Integer, default=30)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    test_case = relationship("TestCase", back_populates="request_steps")
    assertions = relationship("Assertion", back_populates="request_step", cascade="all, delete-orphan")
