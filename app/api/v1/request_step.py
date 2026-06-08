from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.request_step import RequestStep
from app.models.test_case import TestCase
from app.schemas.request_step import RequestStepCreate, RequestStepUpdate, RequestStep as RequestStepSchema
from app.schemas.common import ResponseModel

router = APIRouter(prefix="/request-steps", tags=["请求步骤管理"])


@router.get("/{step_id}", response_model=ResponseModel[RequestStepSchema])
def get_request_step(step_id: int, db: Session = Depends(get_db)):
    step = db.query(RequestStep).filter(RequestStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="请求步骤不存在")
    return ResponseModel(data=step)


@router.post("", response_model=ResponseModel[RequestStepSchema])
def create_request_step(step_in: RequestStepCreate, db: Session = Depends(get_db)):
    case = db.query(TestCase).filter(TestCase.id == step_in.test_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    step = RequestStep(**step_in.model_dump())
    db.add(step)
    db.commit()
    db.refresh(step)
    return ResponseModel(data=step, message="创建成功")


@router.put("/{step_id}", response_model=ResponseModel[RequestStepSchema])
def update_request_step(step_id: int, step_in: RequestStepUpdate, db: Session = Depends(get_db)):
    step = db.query(RequestStep).filter(RequestStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="请求步骤不存在")
    
    update_data = step_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(step, key, value)
    
    db.commit()
    db.refresh(step)
    return ResponseModel(data=step, message="更新成功")


@router.delete("/{step_id}", response_model=ResponseModel)
def delete_request_step(step_id: int, db: Session = Depends(get_db)):
    step = db.query(RequestStep).filter(RequestStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="请求步骤不存在")
    
    db.delete(step)
    db.commit()
    return ResponseModel(message="删除成功")


@router.get("/{step_id}/assertions", response_model=ResponseModel[List])
def get_step_assertions(step_id: int, db: Session = Depends(get_db)):
    step = db.query(RequestStep).filter(RequestStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="请求步骤不存在")
    
    from app.schemas.assertion import Assertion as AssertionSchema
    
    assertions = sorted(step.assertions, key=lambda a: a.order)
    return ResponseModel(data=[AssertionSchema.model_validate(a).model_dump() for a in assertions])


@router.post("/{step_id}/debug", response_model=ResponseModel)
async def debug_request_step(step_id: int, db: Session = Depends(get_db)):
    step = db.query(RequestStep).filter(RequestStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="请求步骤不存在")
    
    from app.core.http_executor import HttpExecutor
    from app.core.assertion_engine import AssertionEngine
    
    variables = {"global": {}}
    
    result = await HttpExecutor.execute(step, variables)
    
    assertion_results = []
    for assertion in sorted(step.assertions, key=lambda a: a.order):
        passed, actual_value, error_msg = AssertionEngine.assert_(
            assertion.assert_type,
            assertion.source,
            assertion.expression,
            assertion.expected_value,
            assertion.comparator,
            result
        )
        assertion_results.append({
            "assertion_id": assertion.id,
            "assertion_name": assertion.name,
            "passed": passed,
            "actual_value": actual_value,
            "expected_value": assertion.expected_value,
            "error_message": error_msg
        })
    
    return ResponseModel(data={
        "request": result.get("request"),
        "response": {
            "status_code": result.get("status_code"),
            "headers": result.get("headers"),
            "body_summary": result.get("body_summary"),
            "duration": result.get("duration")
        },
        "assertion_results": assertion_results,
        "success": result.get("success"),
        "error": result.get("error")
    })
