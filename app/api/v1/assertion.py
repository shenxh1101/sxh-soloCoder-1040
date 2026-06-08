from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assertion import Assertion
from app.models.request_step import RequestStep
from app.schemas.assertion import AssertionCreate, AssertionUpdate, Assertion as AssertionSchema
from app.schemas.common import ResponseModel

router = APIRouter(prefix="/assertions", tags=["断言规则管理"])


@router.get("/{assertion_id}", response_model=ResponseModel[AssertionSchema])
def get_assertion(assertion_id: int, db: Session = Depends(get_db)):
    assertion = db.query(Assertion).filter(Assertion.id == assertion_id).first()
    if not assertion:
        raise HTTPException(status_code=404, detail="断言不存在")
    return ResponseModel(data=assertion)


@router.post("", response_model=ResponseModel[AssertionSchema])
def create_assertion(assertion_in: AssertionCreate, db: Session = Depends(get_db)):
    step = db.query(RequestStep).filter(RequestStep.id == assertion_in.request_step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="请求步骤不存在")
    
    assertion = Assertion(**assertion_in.model_dump())
    db.add(assertion)
    db.commit()
    db.refresh(assertion)
    return ResponseModel(data=assertion, message="创建成功")


@router.put("/{assertion_id}", response_model=ResponseModel[AssertionSchema])
def update_assertion(assertion_id: int, assertion_in: AssertionUpdate, db: Session = Depends(get_db)):
    assertion = db.query(Assertion).filter(Assertion.id == assertion_id).first()
    if not assertion:
        raise HTTPException(status_code=404, detail="断言不存在")
    
    update_data = assertion_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assertion, key, value)
    
    db.commit()
    db.refresh(assertion)
    return ResponseModel(data=assertion, message="更新成功")


@router.delete("/{assertion_id}", response_model=ResponseModel)
def delete_assertion(assertion_id: int, db: Session = Depends(get_db)):
    assertion = db.query(Assertion).filter(Assertion.id == assertion_id).first()
    if not assertion:
        raise HTTPException(status_code=404, detail="断言不存在")
    
    db.delete(assertion)
    db.commit()
    return ResponseModel(message="删除成功")


@router.get("/types", response_model=ResponseModel[List])
def get_assertion_types():
    types = [
        {
            "type": "response_status",
            "name": "响应状态码",
            "description": "验证HTTP响应状态码",
            "comparators": ["equals", "not_equals", "greater_than", "less_than"]
        },
        {
            "type": "response_body",
            "name": "响应体",
            "description": "验证响应体内容",
            "comparators": ["equals", "not_equals", "contains", "not_contains", "matches", "is_null", "is_not_null", "is_empty", "is_not_empty"]
        },
        {
            "type": "response_headers",
            "name": "响应头",
            "description": "验证响应头内容",
            "comparators": ["equals", "not_equals", "contains", "not_contains", "exists"]
        },
        {
            "type": "response_time",
            "name": "响应时间",
            "description": "验证响应时间(ms)",
            "comparators": ["less_than", "greater_than", "less_than_or_equal", "greater_than_or_equal"]
        }
    ]
    
    return ResponseModel(data=types)
