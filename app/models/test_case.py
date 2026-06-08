from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    test_suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=False)
    order = Column(Integer, default=0)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    test_suite = relationship("TestSuite", back_populates="test_cases")
    request_steps = relationship("RequestStep", back_populates="test_case", cascade="all, delete-orphan")
