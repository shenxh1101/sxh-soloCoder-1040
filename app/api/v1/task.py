import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.task import Task
from app.models.project import Project
from app.models.environment import Environment
from app.models.execution_record import ExecutionRecord
from app.schemas.task import TaskCreate, TaskUpdate, Task as TaskSchema, TaskRunRequest
from app.schemas.common import ResponseModel, PageParams, PageResult
from app.core.scheduler import scheduler

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("", response_model=ResponseModel[PageResult[TaskSchema]])
def get_tasks(
    page_params: PageParams = Depends(),
    project_id: Optional[int] = None,
    task_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    if task_type:
        query = query.filter(Task.task_type == task_type)
    
    if is_enabled is not None:
        query = query.filter(Task.is_enabled == is_enabled)
    
    if keyword:
        query = query.filter(Task.name.contains(keyword) | Task.description.contains(keyword))
    
    total = query.count()
    items = query.order_by(Task.id.desc()) \
        .offset((page_params.page - 1) * page_params.page_size) \
        .limit(page_params.page_size) \
        .all()
    
    return ResponseModel(
        data=PageResult(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=(total + page_params.page_size - 1) // page_params.page_size
        )
    )


@router.get("/{task_id}", response_model=ResponseModel[TaskSchema])
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ResponseModel(data=task)


@router.post("", response_model=ResponseModel[TaskSchema])
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == task_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if task_in.environment_id:
        env = db.query(Environment).filter(Environment.id == task_in.environment_id).first()
        if not env:
            raise HTTPException(status_code=404, detail="环境不存在")
    
    if task_in.task_type == "scheduled" and task_in.cron_expression:
        valid, error_msg, _ = scheduler.validate_cron_expression(task_in.cron_expression)
        if not valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    task = Task(**task_in.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    
    if task.task_type == "scheduled" and task.is_enabled and task.cron_expression:
        try:
            scheduler.update_scheduled_task(task)
        except Exception as e:
            db.delete(task)
            db.commit()
            raise HTTPException(status_code=400, detail=str(e))
    
    db.refresh(task)
    return ResponseModel(data=task, message="创建成功")


@router.put("/{task_id}", response_model=ResponseModel[TaskSchema])
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    new_task_type = task_in.task_type if task_in.task_type is not None else task.task_type
    new_cron = task_in.cron_expression if task_in.cron_expression is not None else task.cron_expression
    new_is_enabled = task_in.is_enabled if task_in.is_enabled is not None else task.is_enabled
    
    if new_task_type == "scheduled" and new_cron and new_is_enabled:
        valid, error_msg, _ = scheduler.validate_cron_expression(new_cron)
        if not valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    update_data = task_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    
    try:
        scheduler.update_scheduled_task(task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db.refresh(task)
    return ResponseModel(data=task, message="更新成功")


@router.delete("/{task_id}", response_model=ResponseModel)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    scheduler._remove_scheduled_task(task_id)
    
    db.delete(task)
    db.commit()
    return ResponseModel(message="删除成功")


@router.post("/{task_id}/run", response_model=ResponseModel)
async def run_task(task_id: int, run_request: Optional[TaskRunRequest] = None, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    override_params = run_request.model_dump() if run_request else None
    
    try:
        execution_record_id = await scheduler.run_task_now(task_id, override_params)
        
        execution_record = db.query(ExecutionRecord).filter(ExecutionRecord.id == execution_record_id).first()
        
        return ResponseModel(
            data={"execution_record_id": execution_record.id, "status": execution_record.status},
            message="任务执行完成"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务执行失败: {str(e)}")


@router.post("/{task_id}/run-async", response_model=ResponseModel)
async def run_task_async(task_id: int, run_request: Optional[TaskRunRequest] = None, 
                   db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    environment_id = task.environment_id
    if run_request and run_request.environment_id:
        environment_id = run_request.environment_id
    
    execution_record = ExecutionRecord(
        task_id=task.id,
        project_id=task.project_id,
        environment_id=environment_id,
        trigger_type="manual",
        status="pending",
        total_cases=0,
        passed_cases=0,
        failed_cases=0,
        skipped_cases=0,
        pass_rate=0.0,
        total_duration=0.0
    )
    db.add(execution_record)
    db.commit()
    db.refresh(execution_record)
    
    override_params = run_request.model_dump() if run_request else None
    record_id = execution_record.id
    
    async def execute_background():
        try:
            await scheduler.run_task_now(task_id, override_params, record_id)
        except Exception as e:
            print(f"后台执行任务失败: {str(e)}")
    
    import asyncio
    asyncio.create_task(execute_background())
    
    return ResponseModel(
        data={"execution_record_id": execution_record.id, "status": "pending"},
        message="任务已提交，正在后台执行"
    )


@router.post("/{task_id}/enable", response_model=ResponseModel[TaskSchema])
def enable_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.task_type == "scheduled" and task.cron_expression:
        valid, error_msg, _ = scheduler.validate_cron_expression(task.cron_expression)
        if not valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    task.is_enabled = True
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    
    try:
        scheduler.update_scheduled_task(task)
    except Exception as e:
        task.is_enabled = False
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))
    
    db.refresh(task)
    return ResponseModel(data=task, message="任务已启用")


@router.post("/{task_id}/disable", response_model=ResponseModel[TaskSchema])
def disable_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task.is_enabled = False
    task.next_run_at = None
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    
    scheduler.update_scheduled_task(task)
    
    db.refresh(task)
    return ResponseModel(data=task, message="任务已禁用")


@router.get("/{task_id}/executions", response_model=ResponseModel[List])
def get_task_executions(task_id: int, limit: int = 10, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    executions = db.query(ExecutionRecord) \
        .filter(ExecutionRecord.task_id == task_id) \
        .order_by(ExecutionRecord.id.desc()) \
        .limit(limit) \
        .all()
    
    from app.schemas.execution_record import ExecutionRecord as ExecutionRecordSchema
    
    return ResponseModel(data=[ExecutionRecordSchema.model_validate(e).model_dump() for e in executions])
