from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AssertionResult(BaseModel):
    assertion_id: int = Field(description="断言ID")
    assertion_name: str = Field(description="断言名称")
    passed: bool = Field(description="是否通过")
    actual_value: Optional[str] = Field(None, description="实际值")
    expected_value: Optional[str] = Field(None, description="期望值")
    error_message: Optional[str] = Field(None, description="错误信息")


class StepResultDetail(BaseModel):
    id: int
    case_result_id: int
    request_step_id: int
    request_step_name: str
    status: str
    duration: float
    request_url: Optional[str]
    request_method: Optional[str]
    request_headers: Optional[Dict[str, Any]]
    request_body: Optional[str]
    response_status: Optional[int]
    response_headers: Optional[Dict[str, Any]]
    response_body: Optional[str]
    response_body_summary: Optional[str]
    error_message: Optional[str]
    assertion_results: List[AssertionResult]
    extracted_variables: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class CaseResultDetail(BaseModel):
    id: int
    execution_record_id: int
    test_case_id: int
    test_case_name: str
    status: str
    duration: float
    error_message: Optional[str]
    step_results: List[StepResultDetail]
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionRecordBase(BaseModel):
    task_id: Optional[int]
    project_id: int
    environment_id: Optional[int]
    trigger_type: str
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    skipped_cases: int
    pass_rate: float
    total_duration: float
    started_at: datetime
    finished_at: Optional[datetime]
    retry_attempt: int
    error_message: Optional[str]


class ExecutionRecord(ExecutionRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionRecordDetail(ExecutionRecord):
    case_results: List[CaseResultDetail] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ExecutionRecordSummary(BaseModel):
    id: int
    task_id: Optional[int]
    task_name: Optional[str]
    project_id: int
    project_name: str
    environment_name: Optional[str]
    trigger_type: str
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    skipped_cases: int
    pass_rate: float
    total_duration: float
    started_at: datetime
    finished_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class FailedStepSummary(BaseModel):
    step_name: str
    error_message: str
    request_url: Optional[str]
    response_status: Optional[int]
    response_body_summary: Optional[str]


class ReportResponse(BaseModel):
    execution_record: ExecutionRecordDetail
    failed_steps: List[FailedStepSummary]
    history_comparison: Optional[Dict[str, Any]] = None


class RecentIssuesQuery(BaseModel):
    project_id: int
    days: Optional[int] = Field(default=7, description="查询天数")
