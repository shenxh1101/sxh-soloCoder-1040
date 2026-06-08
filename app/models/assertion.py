from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Assertion(Base):
    __tablename__ = "assertions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    request_step_id = Column(Integer, ForeignKey("request_steps.id"), nullable=False)
    
    assert_type = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    expression = Column(String(500), nullable=True)
    expected_value = Column(Text, nullable=True)
    comparator = Column(String(30), nullable=False, default="equals")
    
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    request_step = relationship("RequestStep", back_populates="assertions")
