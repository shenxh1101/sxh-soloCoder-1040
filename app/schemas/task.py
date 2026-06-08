from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    name: str = Field(..., max_length=100, description="任务名称")
    project_id: int = Field(..., description="项目ID")
    description: Optional[str] = Field(None, description="描述")
    task_type: str = Field(default="single", max_length=20, description="任务类型: single/scheduled/tag_based")
    cron_expression: Optional[str] = Field(None, max_length=100, description="cron表达式")
    test_suite_ids: Optional[List[int]] = Field(default_factory=list, description="测试套件ID列表")
    test_case_ids: Optional[List[int]] = Field(default_factory=list, description="测试用例ID列表")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    environment_id: Optional[int] = Field(None, description="环境ID")
    retry_count: Optional[int] = Field(default=0, description="重试次数")
    retry_interval: Optional[int] = Field(default=5, description="重试间隔(秒)")
    run_parallel: Optional[bool] = Field(default=False, description="是否并行执行")
    is_enabled: Optional[bool] = Field(default=True, description="是否启用")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="任务名称")
    description: Optional[str] = Field(None, description="描述")
    task_type: Optional[str] = Field(None, max_length=20, description="任务类型")
    cron_expression: Optional[str] = Field(None, max_length=100, description="cron表达式")
    test_suite_ids: Optional[List[int]] = Field(None, description="测试套件ID列表")
    test_case_ids: Optional[List[int]] = Field(None, description="测试用例ID列表")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    environment_id: Optional[int] = Field(None, description="环境ID")
    retry_count: Optional[int] = Field(None, description="重试次数")
    retry_interval: Optional[int] = Field(None, description="重试间隔(秒)")
    run_parallel: Optional[bool] = Field(None, description="是否并行执行")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class Task(TaskBase):
    id: int
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskRunRequest(BaseModel):
    environment_id: Optional[int] = Field(None, description="运行环境ID")
    test_suite_ids: Optional[List[int]] = Field(None, description="指定运行的测试套件ID")
    test_case_ids: Optional[List[int]] = Field(None, description="指定运行的测试用例ID")
    tags: Optional[List[str]] = Field(None, description="指定运行的标签")
