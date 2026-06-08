from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EnvironmentVariableBase(BaseModel):
    key: str = Field(..., max_length=100, description="变量名")
    value: Optional[str] = Field(None, description="变量值")
    is_secret: Optional[bool] = Field(default=False, description="是否加密")
    description: Optional[str] = Field(None, max_length=500, description="描述")


class EnvironmentVariableCreate(EnvironmentVariableBase):
    pass


class EnvironmentVariableUpdate(BaseModel):
    key: Optional[str] = Field(None, max_length=100, description="变量名")
    value: Optional[str] = Field(None, description="变量值")
    is_secret: Optional[bool] = Field(None, description="是否加密")
    description: Optional[str] = Field(None, max_length=500, description="描述")


class EnvironmentVariable(EnvironmentVariableBase):
    id: int
    environment_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EnvironmentVariableOut(EnvironmentVariableBase):
    id: int
    environment_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EnvironmentBase(BaseModel):
    name: str = Field(..., max_length=100, description="环境名称")
    project_id: int = Field(..., description="项目ID")
    description: Optional[str] = Field(None, description="描述")
    base_url: Optional[str] = Field(None, max_length=500, description="基础URL")
    is_default: Optional[bool] = Field(default=False, description="是否默认环境")


class EnvironmentCreate(EnvironmentBase):
    variables: Optional[List[EnvironmentVariableCreate]] = Field(default_factory=list, description="环境变量列表")


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="环境名称")
    description: Optional[str] = Field(None, description="描述")
    base_url: Optional[str] = Field(None, max_length=500, description="基础URL")
    is_default: Optional[bool] = Field(None, description="是否默认环境")


class Environment(EnvironmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    variables: List[EnvironmentVariable] = Field(default_factory=list)

    class Config:
        from_attributes = True


class EnvironmentOut(EnvironmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    variables: List[EnvironmentVariableOut] = Field(default_factory=list)

    class Config:
        from_attributes = True
