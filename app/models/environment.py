from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=True)
    base_url = Column(String(500), nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project")
    variables = relationship("EnvironmentVariable", back_populates="environment", cascade="all, delete-orphan")


class EnvironmentVariable(Base):
    __tablename__ = "environment_variables"

    id = Column(Integer, primary_key=True, index=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    environment = relationship("Environment", back_populates="variables")
