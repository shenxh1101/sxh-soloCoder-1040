from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from app.database import get_db
from app.models.execution_record import ExecutionRecord, CaseResult, StepResult
from app.models.project import Project
from app.models.task import Task
from app.models.environment import Environment
from app.schemas.execution_record import (
    ExecutionRecord as ExecutionRecordSchema,
    ExecutionRecordDetail as ExecutionRecordDetailSchema,
    ExecutionRecordSummary,
    ReportResponse,
    FailedStepSummary,
    CaseResultDetail,
    StepResultDetail,
    AssertionResult
)
from app.schemas.common import ResponseModel, PageParams, PageResult

router = APIRouter(prefix="/execution-records", tags=["执行记录与报告"])


@router.get("", response_model=ResponseModel[PageResult[ExecutionRecordSummary]])
def get_execution_records(
    page_params: PageParams = Depends(),
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    status: Optional[str] = None,
    trigger_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        ExecutionRecord,
        Project.name.label("project_name"),
        Task.name.label("task_name"),
        Environment.name.label("environment_name")
    ).outerjoin(Project, ExecutionRecord.project_id == Project.id) \
     .outerjoin(Task, ExecutionRecord.task_id == Task.id) \
     .outerjoin(Environment, ExecutionRecord.environment_id == Environment.id)
    
    if project_id:
        query = query.filter(ExecutionRecord.project_id == project_id)
    
    if task_id:
        query = query.filter(ExecutionRecord.task_id == task_id)
    
    if status:
        query = query.filter(ExecutionRecord.status == status)
    
    if trigger_type:
        query = query.filter(ExecutionRecord.trigger_type == trigger_type)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ExecutionRecord.started_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(ExecutionRecord.started_at < end_dt)
        except ValueError:
            pass
    
    total = query.count()
    results = query.order_by(ExecutionRecord.id.desc()) \
        .offset((page_params.page - 1) * page_params.page_size) \
        .limit(page_params.page_size) \
        .all()
    
    items = []
    for record, project_name, task_name, env_name in results:
        record_dict = ExecutionRecordSchema.model_validate(record).model_dump()
        record_dict["project_name"] = project_name
        record_dict["task_name"] = task_name
        record_dict["environment_name"] = env_name
        items.append(ExecutionRecordSummary(**record_dict))
    
    return ResponseModel(
        data=PageResult(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=(total + page_params.page_size - 1) // page_params.page_size
        )
    )


@router.get("/{record_id}", response_model=ResponseModel[ExecutionRecordDetailSchema])
def get_execution_record_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(ExecutionRecord).filter(ExecutionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    case_results = db.query(CaseResult).filter(CaseResult.execution_record_id == record_id) \
        .order_by(CaseResult.id).all()
    
    case_result_details = []
    for cr in case_results:
        step_results = db.query(StepResult).filter(StepResult.case_result_id == cr.id) \
            .order_by(StepResult.id).all()
        
        step_result_details = []
        for sr in step_results:
            assertion_results = []
            for ar in sr.assertion_results or []:
                assertion_results.append(AssertionResult(**ar))
            
            step_result_details.append(StepResultDetail(
                id=sr.id,
                case_result_id=sr.case_result_id,
                request_step_id=sr.request_step_id,
                request_step_name=sr.request_step_name,
                status=sr.status,
                duration=sr.duration,
                request_url=sr.request_url,
                request_method=sr.request_method,
                request_headers=sr.request_headers,
                request_body=sr.request_body,
                response_status=sr.response_status,
                response_headers=sr.response_headers,
                response_body=sr.response_body,
                response_body_summary=sr.response_body_summary,
                error_message=sr.error_message,
                assertion_results=assertion_results,
                extracted_variables=sr.extracted_variables,
                created_at=sr.created_at
            ))
        
        case_result_details.append(CaseResultDetail(
            id=cr.id,
            execution_record_id=cr.execution_record_id,
            test_case_id=cr.test_case_id,
            test_case_name=cr.test_case_name,
            status=cr.status,
            duration=cr.duration,
            error_message=cr.error_message,
            step_results=step_result_details,
            created_at=cr.created_at
        ))
    
    record_dict = ExecutionRecordSchema.model_validate(record).model_dump()
    record_dict["case_results"] = case_result_details
    
    return ResponseModel(data=ExecutionRecordDetailSchema(**record_dict))


@router.get("/{record_id}/report", response_model=ResponseModel[ReportResponse])
def get_execution_report(record_id: int, db: Session = Depends(get_db)):
    record = db.query(ExecutionRecord).filter(ExecutionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    case_results = db.query(CaseResult).filter(CaseResult.execution_record_id == record_id) \
        .order_by(CaseResult.id).all()
    
    case_result_details = []
    failed_steps = []
    
    for cr in case_results:
        step_results = db.query(StepResult).filter(StepResult.case_result_id == cr.id) \
            .order_by(StepResult.id).all()
        
        step_result_details = []
        for sr in step_results:
            assertion_results = []
            for ar in sr.assertion_results or []:
                assertion_results.append(AssertionResult(**ar))
            
            if sr.status == "failed":
                failed_steps.append(FailedStepSummary(
                    step_name=sr.request_step_name,
                    error_message=sr.error_message or "未知错误",
                    request_url=sr.request_url,
                    response_status=sr.response_status,
                    response_body_summary=sr.response_body_summary
                ))
            
            step_result_details.append(StepResultDetail(
                id=sr.id,
                case_result_id=sr.case_result_id,
                request_step_id=sr.request_step_id,
                request_step_name=sr.request_step_name,
                status=sr.status,
                duration=sr.duration,
                request_url=sr.request_url,
                request_method=sr.request_method,
                request_headers=sr.request_headers,
                request_body=sr.request_body,
                response_status=sr.response_status,
                response_headers=sr.response_headers,
                response_body=sr.response_body,
                response_body_summary=sr.response_body_summary,
                error_message=sr.error_message,
                assertion_results=assertion_results,
                extracted_variables=sr.extracted_variables,
                created_at=sr.created_at
            ))
        
        case_result_details.append(CaseResultDetail(
            id=cr.id,
            execution_record_id=cr.execution_record_id,
            test_case_id=cr.test_case_id,
            test_case_name=cr.test_case_name,
            status=cr.status,
            duration=cr.duration,
            error_message=cr.error_message,
            step_results=step_result_details,
            created_at=cr.created_at
        ))
    
    record_dict = ExecutionRecordSchema.model_validate(record).model_dump()
    record_dict["case_results"] = case_result_details
    record_detail = ExecutionRecordDetailSchema(**record_dict)
    
    history_comparison = _get_history_comparison(db, record)
    
    return ResponseModel(data=ReportResponse(
        execution_record=record_detail,
        failed_steps=failed_steps,
        history_comparison=history_comparison
    ))


def _get_history_comparison(db: Session, current_record: ExecutionRecord) -> Optional[dict]:
    try:
        previous_records = db.query(ExecutionRecord).filter(
            ExecutionRecord.project_id == current_record.project_id,
            ExecutionRecord.task_id == current_record.task_id,
            ExecutionRecord.id < current_record.id,
            ExecutionRecord.status.in_(["passed", "failed"])
        ).order_by(ExecutionRecord.id.desc()).limit(5).all()
        
        if not previous_records:
            return None
        
        history_stats = []
        for prev in previous_records:
            history_stats.append({
                "execution_id": prev.id,
                "date": prev.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "pass_rate": prev.pass_rate,
                "total_cases": prev.total_cases,
                "failed_cases": prev.failed_cases,
                "duration": prev.total_duration,
                "status": prev.status
            })
        
        avg_pass_rate = sum(r["pass_rate"] for r in history_stats) / len(history_stats)
        pass_rate_trend = current_record.pass_rate - avg_pass_rate
        
        avg_duration = sum(r["duration"] for r in history_stats) / len(history_stats)
        duration_trend = current_record.total_duration - avg_duration
        
        return {
            "recent_runs": history_stats,
            "avg_pass_rate": round(avg_pass_rate, 2),
            "pass_rate_trend": round(pass_rate_trend, 2),
            "avg_duration": round(avg_duration, 2),
            "duration_trend": round(duration_trend, 2)
        }
    except Exception as e:
        return None


@router.get("/{record_id}/failed-steps", response_model=ResponseModel[List[FailedStepSummary]])
def get_failed_steps(record_id: int, db: Session = Depends(get_db)):
    record = db.query(ExecutionRecord).filter(ExecutionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    failed_steps = []
    
    case_results = db.query(CaseResult).filter(CaseResult.execution_record_id == record_id).all()
    for cr in case_results:
        step_results = db.query(StepResult).filter(
            StepResult.case_result_id == cr.id,
            StepResult.status == "failed"
        ).all()
        
        for sr in step_results:
            failed_steps.append(FailedStepSummary(
                step_name=sr.request_step_name,
                error_message=sr.error_message or "未知错误",
                request_url=sr.request_url,
                response_status=sr.response_status,
                response_body_summary=sr.response_body_summary
            ))
    
    return ResponseModel(data=failed_steps)


@router.get("/project/{project_id}/recent-issues", response_model=ResponseModel)
def get_recent_issues(
    project_id: int,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    start_date = datetime.now() - timedelta(days=days)
    
    failed_executions = db.query(ExecutionRecord).filter(
        ExecutionRecord.project_id == project_id,
        ExecutionRecord.status.in_(["failed", "error"]),
        ExecutionRecord.started_at >= start_date
    ).order_by(ExecutionRecord.id.desc()).all()
    
    issues = []
    for exec_record in failed_executions:
        failed_cases = db.query(CaseResult).filter(
            CaseResult.execution_record_id == exec_record.id,
            CaseResult.status == "failed"
        ).all()
        
        failed_case_names = [fc.test_case_name for fc in failed_cases]
        
        issues.append({
            "execution_id": exec_record.id,
            "task_id": exec_record.task_id,
            "task_name": exec_record.task.name if exec_record.task else "未知任务",
            "failed_at": exec_record.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "total_cases": exec_record.total_cases,
            "failed_cases": exec_record.failed_cases,
            "pass_rate": exec_record.pass_rate,
            "failed_case_names": failed_case_names,
            "error_message": exec_record.error_message
        })
    
    total_failures = len(failed_executions)
    total_failed_cases = sum(exec.failed_cases for exec in failed_executions)
    
    return ResponseModel(data={
        "project_id": project_id,
        "project_name": project.name,
        "query_days": days,
        "total_failures": total_failures,
        "total_failed_cases": total_failed_cases,
        "issues": issues
    })


@router.get("/project/{project_id}/statistics", response_model=ResponseModel)
def get_project_statistics(
    project_id: int,
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    start_date = datetime.now() - timedelta(days=days)
    
    records = db.query(ExecutionRecord).filter(
        ExecutionRecord.project_id == project_id,
        ExecutionRecord.started_at >= start_date
    ).all()
    
    if not records:
        return ResponseModel(data={
            "project_id": project_id,
            "project_name": project.name,
            "query_days": days,
            "total_executions": 0,
            "pass_rate": 0,
            "avg_duration": 0,
            "total_cases_run": 0,
            "status_distribution": {},
            "daily_trend": []
        })
    
    total_executions = len(records)
    passed_executions = sum(1 for r in records if r.status == "passed")
    total_cases_run = sum(r.total_cases for r in records)
    avg_pass_rate = sum(r.pass_rate for r in records) / total_executions
    avg_duration = sum(r.total_duration for r in records) / total_executions
    
    status_distribution = {}
    for r in records:
        status_distribution[r.status] = status_distribution.get(r.status, 0) + 1
    
    daily_data = {}
    for r in records:
        date_key = r.started_at.strftime("%Y-%m-%d")
        if date_key not in daily_data:
            daily_data[date_key] = {"count": 0, "pass_rate_sum": 0}
        daily_data[date_key]["count"] += 1
        daily_data[date_key]["pass_rate_sum"] += r.pass_rate
    
    daily_trend = []
    for date in sorted(daily_data.keys()):
        daily_trend.append({
            "date": date,
            "executions": daily_data[date]["count"],
            "avg_pass_rate": round(daily_data[date]["pass_rate_sum"] / daily_data[date]["count"], 2)
        })
    
    return ResponseModel(data={
        "project_id": project_id,
        "project_name": project.name,
        "query_days": days,
        "total_executions": total_executions,
        "passed_executions": passed_executions,
        "failed_executions": total_executions - passed_executions,
        "pass_rate": round((passed_executions / total_executions * 100) if total_executions else 0, 2),
        "avg_pass_rate_per_execution": round(avg_pass_rate, 2),
        "avg_duration": round(avg_duration, 2),
        "total_cases_run": total_cases_run,
        "status_distribution": status_distribution,
        "daily_trend": daily_trend
    })
