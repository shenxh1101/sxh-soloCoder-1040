from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TestCaseBase(BaseModel):
    name: str = Field(..., max_length=100, description="测试用例名称")
    description: Optional[str] = Field(None, description="描述")
    test_suite_id: int = Field(..., description="测试套件ID")
    order: Optional[int] = Field(default=0, description="排序")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="测试用例名称")
    description: Optional[str] = Field(None, description="描述")
    order: Optional[int] = Field(None, description="排序")
    tags: Optional[List[str]] = Field(None, description="标签")


class TestCase(TestCaseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TestCaseWithSteps(TestCase):
    step_count: int = Field(default=0, description="步骤数量")
