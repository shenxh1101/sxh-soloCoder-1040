from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.notification import NotificationConfig, NotificationRecord
from app.models.project import Project
from app.schemas.notification import (
    NotificationConfigCreate,
    NotificationConfigUpdate,
    NotificationConfig as NotificationConfigSchema,
    NotificationRecord as NotificationRecordSchema
)
from app.schemas.common import ResponseModel, PageParams, PageResult
from app.core.notification_sender import NotificationSender
from app.models.execution_record import ExecutionRecord

router = APIRouter(prefix="/notifications", tags=["通知配置"])


@router.get("/configs", response_model=ResponseModel[PageResult[NotificationConfigSchema]])
def get_notification_configs(
    page_params: PageParams = Depends(),
    project_id: Optional[int] = None,
    notify_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(NotificationConfig)
    
    if project_id:
        query = query.filter(NotificationConfig.project_id == project_id)
    
    if notify_type:
        query = query.filter(NotificationConfig.notify_type == notify_type)
    
    if is_enabled is not None:
        query = query.filter(NotificationConfig.is_enabled == is_enabled)
    
    total = query.count()
    items = query.order_by(NotificationConfig.id.desc()) \
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


@router.get("/configs/{config_id}", response_model=ResponseModel[NotificationConfigSchema])
def get_notification_config(config_id: int, db: Session = Depends(get_db)):
    config = db.query(NotificationConfig).filter(NotificationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="通知配置不存在")
    return ResponseModel(data=config)


@router.post("/configs", response_model=ResponseModel[NotificationConfigSchema])
def create_notification_config(config_in: NotificationConfigCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == config_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    valid_types = ["dingtalk", "wechat", "webhook", "email"]
    if config_in.notify_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"通知类型必须是: {', '.join(valid_types)}")
    
    valid_when = ["always", "on_failure", "never"]
    if config_in.notify_when not in valid_when:
        raise HTTPException(status_code=400, detail=f"通知时机必须是: {', '.join(valid_when)}")
    
    config = NotificationConfig(**config_in.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return ResponseModel(data=config, message="创建成功")


@router.put("/configs/{config_id}", response_model=ResponseModel[NotificationConfigSchema])
def update_notification_config(config_id: int, config_in: NotificationConfigUpdate, db: Session = Depends(get_db)):
    config = db.query(NotificationConfig).filter(NotificationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="通知配置不存在")
    
    update_data = config_in.model_dump(exclude_unset=True)
    
    if "notify_type" in update_data:
        valid_types = ["dingtalk", "wechat", "webhook", "email"]
        if update_data["notify_type"] not in valid_types:
            raise HTTPException(status_code=400, detail=f"通知类型必须是: {', '.join(valid_types)}")
    
    if "notify_when" in update_data:
        valid_when = ["always", "on_failure", "never"]
        if update_data["notify_when"] not in valid_when:
            raise HTTPException(status_code=400, detail=f"通知时机必须是: {', '.join(valid_when)}")
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    config.updated_at = datetime.now()
    db.commit()
    db.refresh(config)
    return ResponseModel(data=config, message="更新成功")


@router.delete("/configs/{config_id}", response_model=ResponseModel)
def delete_notification_config(config_id: int, db: Session = Depends(get_db)):
    config = db.query(NotificationConfig).filter(NotificationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="通知配置不存在")
    
    db.delete(config)
    db.commit()
    return ResponseModel(message="删除成功")


@router.post("/configs/{config_id}/test", response_model=ResponseModel)
async def test_notification_config(config_id: int, db: Session = Depends(get_db)):
    config = db.query(NotificationConfig).filter(NotificationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="通知配置不存在")
    
    mock_execution = ExecutionRecord(
        id=0,
        project_id=config.project_id,
        task_id=None,
        environment_id=None,
        trigger_type="test",
        status="failed",
        total_cases=10,
        passed_cases=7,
        failed_cases=3,
        skipped_cases=0,
        pass_rate=70.0,
        total_duration=1234.56,
        started_at=datetime.now(),
        finished_at=datetime.now(),
        retry_attempt=0
    )
    mock_execution.project = Project(name="测试项目", id=config.project_id)
    mock_execution.environment = None
    
    mock_failed_steps = [
        {
            "step_name": "用户登录接口",
            "error_message": "断言失败: 期望状态码200，实际401",
            "request_url": "https://api.example.com/login",
            "response_status": 401,
            "response_body_summary": '{"code":401,"message":"用户名或密码错误"}'
        }
    ]
    
    result = await NotificationSender.send_notification(
        config=config,
        execution_record=mock_execution,
        failed_steps=mock_failed_steps
    )
    
    notify_record = NotificationRecord(
        notification_config_id=config.id,
        execution_record_id=None,
        project_id=config.project_id,
        title="测试通知 - 自动化测试执行结果",
        content="这是一条测试通知消息",
        notify_type=config.notify_type,
        status="sent" if result.get("success") else "failed",
        error_message=result.get("error"),
        assignees=config.assignees or [],
        sent_at=datetime.now()
    )
    db.add(notify_record)
    db.commit()
    
    if result.get("success"):
        return ResponseModel(data=result, message="测试通知发送成功")
    else:
        return ResponseModel(code=500, data=result, message=f"测试通知发送失败: {result.get('error')}")


@router.get("/records", response_model=ResponseModel[PageResult[NotificationRecordSchema]])
def get_notification_records(
    page_params: PageParams = Depends(),
    project_id: Optional[int] = None,
    notify_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(NotificationRecord)
    
    if project_id:
        query = query.filter(NotificationRecord.project_id == project_id)
    
    if notify_type:
        query = query.filter(NotificationRecord.notify_type == notify_type)
    
    if status:
        query = query.filter(NotificationRecord.status == status)
    
    total = query.count()
    items = query.order_by(NotificationRecord.id.desc()) \
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


@router.get("/types", response_model=ResponseModel[List])
def get_notification_types():
    types = [
        {
            "type": "dingtalk",
            "name": "钉钉群机器人",
            "description": "通过钉钉群机器人Webhook发送通知",
            "required_fields": ["webhook_url"],
            "optional_fields": ["secret_key", "at_mobiles", "at_all"]
        },
        {
            "type": "wechat",
            "name": "企业微信群机器人",
            "description": "通过企业微信群机器人Webhook发送通知",
            "required_fields": ["webhook_url"],
            "optional_fields": ["at_mobiles"]
        },
        {
            "type": "webhook",
            "name": "自定义Webhook",
            "description": "通过自定义HTTP Webhook发送通知",
            "required_fields": ["webhook_url"],
            "optional_fields": ["secret_key"]
        },
        {
            "type": "email",
            "name": "邮件",
            "description": "通过邮件发送通知",
            "required_fields": ["assignees"],
            "optional_fields": []
        }
    ]
    
    return ResponseModel(data=types)
