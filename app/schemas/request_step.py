from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class RequestStepBase(BaseModel):
    name: str = Field(..., max_length=100, description="步骤名称")
    test_case_id: int = Field(..., description="测试用例ID")
    order: Optional[int] = Field(default=0, description="排序")
    method: str = Field(default="GET", max_length=10, description="HTTP方法")
    url: str = Field(..., max_length=500, description="请求URL")
    headers: Optional[Dict[str, Any]] = Field(default_factory=dict, description="请求头")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="查询参数")
    body: Optional[str] = Field(None, description="请求体")
    body_type: Optional[str] = Field(default="json", max_length=20, description="请求体类型")
    extract_variables: Optional[Dict[str, str]] = Field(default_factory=dict, description="提取变量")
    skip_on_failure: Optional[bool] = Field(default=False, description="失败时跳过")
    timeout: Optional[int] = Field(default=30, description="超时时间(秒)")


class RequestStepCreate(RequestStepBase):
    pass


class RequestStepUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="步骤名称")
    order: Optional[int] = Field(None, description="排序")
    method: Optional[str] = Field(None, max_length=10, description="HTTP方法")
    url: Optional[str] = Field(None, max_length=500, description="请求URL")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(None, description="查询参数")
    body: Optional[str] = Field(None, description="请求体")
    body_type: Optional[str] = Field(None, max_length=20, description="请求体类型")
    extract_variables: Optional[Dict[str, str]] = Field(None, description="提取变量")
    skip_on_failure: Optional[bool] = Field(None, description="失败时跳过")
    timeout: Optional[int] = Field(None, description="超时时间(秒)")


class RequestStep(RequestStepBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
