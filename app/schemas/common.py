from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    code: int = Field(default=200, description="响应码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class PageResult(BaseModel, Generic[T]):
    items: List[T] = Field(description="数据列表")
    total: int = Field(description="总条数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页条数")
    total_pages: int = Field(description="总页数")
