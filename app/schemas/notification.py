from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NotificationConfigBase(BaseModel):
    project_id: int = Field(..., description="项目ID")
    name: str = Field(..., max_length=100, description="配置名称")
    notify_type: str = Field(..., max_length=20, description="通知类型: dingtalk/wechat/email/webhook")
    notify_when: str = Field(default="on_failure", max_length=20, description="通知时机: always/on_failure/never")
    webhook_url: Optional[str] = Field(None, max_length=500, description="Webhook地址")
    secret_key: Optional[str] = Field(None, max_length=200, description="密钥")
    at_mobiles: Optional[List[str]] = Field(default_factory=list, description="@手机号列表")
    at_all: Optional[bool] = Field(default=False, description="是否@所有人")
    assignees: Optional[List[str]] = Field(default_factory=list, description="负责人列表")
    is_enabled: Optional[bool] = Field(default=True, description="是否启用")


class NotificationConfigCreate(NotificationConfigBase):
    pass


class NotificationConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="配置名称")
    notify_type: Optional[str] = Field(None, max_length=20, description="通知类型")
    notify_when: Optional[str] = Field(None, max_length=20, description="通知时机")
    webhook_url: Optional[str] = Field(None, max_length=500, description="Webhook地址")
    secret_key: Optional[str] = Field(None, max_length=200, description="密钥")
    at_mobiles: Optional[List[str]] = Field(None, description="@手机号列表")
    at_all: Optional[bool] = Field(None, description="是否@所有人")
    assignees: Optional[List[str]] = Field(None, description="负责人列表")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class NotificationConfig(NotificationConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationRecordBase(BaseModel):
    notification_config_id: Optional[int]
    execution_record_id: Optional[int]
    project_id: int
    title: str
    content: str
    notify_type: str
    status: str
    error_message: Optional[str]
    assignees: List[str]
    sent_at: Optional[datetime]


class NotificationRecord(NotificationRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
