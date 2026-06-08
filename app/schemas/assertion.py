from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AssertionBase(BaseModel):
    name: str = Field(..., max_length=100, description="断言名称")
    request_step_id: int = Field(..., description="请求步骤ID")
    assert_type: str = Field(..., max_length=50, description="断言类型")
    source: str = Field(..., max_length=50, description="数据源")
    expression: Optional[str] = Field(None, max_length=500, description="表达式")
    expected_value: Optional[str] = Field(None, description="期望值")
    comparator: str = Field(default="equals", max_length=30, description="比较器")
    order: Optional[int] = Field(default=0, description="排序")


class AssertionCreate(AssertionBase):
    pass


class AssertionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="断言名称")
    assert_type: Optional[str] = Field(None, max_length=50, description="断言类型")
    source: Optional[str] = Field(None, max_length=50, description="数据源")
    expression: Optional[str] = Field(None, max_length=500, description="表达式")
    expected_value: Optional[str] = Field(None, description="期望值")
    comparator: Optional[str] = Field(None, max_length=30, description="比较器")
    order: Optional[int] = Field(None, description="排序")


class Assertion(AssertionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
