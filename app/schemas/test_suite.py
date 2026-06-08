from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TestSuiteBase(BaseModel):
    name: str = Field(..., max_length=100, description="测试套件名称")
    description: Optional[str] = Field(None, description="描述")
    project_id: int = Field(..., description="项目ID")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")


class TestSuiteCreate(TestSuiteBase):
    pass


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="测试套件名称")
    description: Optional[str] = Field(None, description="描述")
    tags: Optional[List[str]] = Field(None, description="标签")


class TestSuite(TestSuiteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TestSuiteWithStats(TestSuite):
    case_count: int = Field(default=0, description="用例数量")
