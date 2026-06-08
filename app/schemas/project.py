from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    owner: Optional[str] = Field(None, max_length=50, description="负责人")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
