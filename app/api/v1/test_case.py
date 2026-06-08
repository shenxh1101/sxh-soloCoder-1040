from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.request_step import RequestStep
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate, TestCase as TestCaseSchema, TestCaseWithSteps
from app.schemas.common import ResponseModel, PageParams, PageResult

router = APIRouter(prefix="/test-cases", tags=["测试用例管理"])


@router.get("", response_model=ResponseModel[PageResult[TestCaseWithSteps]])
def get_test_cases(
    page_params: PageParams = Depends(),
    test_suite_id: Optional[int] = None,
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        TestCase,
        func.count(RequestStep.id).label("step_count")
    ).outerjoin(RequestStep, TestCase.id == RequestStep.test_case_id)
    
    if test_suite_id:
        query = query.filter(TestCase.test_suite_id == test_suite_id)
    
    if keyword:
        query = query.filter(TestCase.name.contains(keyword) | TestCase.description.contains(keyword))
    
    if tag:
        query = query.filter(TestCase.tags.contains([tag]))
    
    query = query.group_by(TestCase.id)
    
    total = query.count()
    results = query.order_by(TestCase.order, TestCase.id.desc()) \
        .offset((page_params.page - 1) * page_params.page_size) \
        .limit(page_params.page_size) \
        .all()
    
    items = []
    for case, step_count in results:
        case_dict = TestCaseSchema.model_validate(case).model_dump()
        case_dict["step_count"] = step_count
        items.append(TestCaseWithSteps(**case_dict))
    
    return ResponseModel(
        data=PageResult(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=(total + page_params.page_size - 1) // page_params.page_size
        )
    )


@router.get("/{case_id}", response_model=ResponseModel[TestCaseWithSteps])
def get_test_case(case_id: int, db: Session = Depends(get_db)):
    result = db.query(
        TestCase,
        func.count(RequestStep.id).label("step_count")
    ).outerjoin(RequestStep, TestCase.id == RequestStep.test_case_id) \
     .filter(TestCase.id == case_id) \
     .group_by(TestCase.id) \
     .first()
    
    if not result:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    case, step_count = result
    case_dict = TestCaseSchema.model_validate(case).model_dump()
    case_dict["step_count"] = step_count
    
    return ResponseModel(data=TestCaseWithSteps(**case_dict))


@router.post("", response_model=ResponseModel[TestCaseSchema])
def create_test_case(case_in: TestCaseCreate, db: Session = Depends(get_db)):
    suite = db.query(TestSuite).filter(TestSuite.id == case_in.test_suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    
    case = TestCase(**case_in.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return ResponseModel(data=case, message="创建成功")


@router.put("/{case_id}", response_model=ResponseModel[TestCaseSchema])
def update_test_case(case_id: int, case_in: TestCaseUpdate, db: Session = Depends(get_db)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    update_data = case_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(case, key, value)
    
    db.commit()
    db.refresh(case)
    return ResponseModel(data=case, message="更新成功")


@router.delete("/{case_id}", response_model=ResponseModel)
def delete_test_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    db.delete(case)
    db.commit()
    return ResponseModel(message="删除成功")


@router.get("/{case_id}/steps", response_model=ResponseModel[List])
def get_case_steps(case_id: int, db: Session = Depends(get_db)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    from app.schemas.request_step import RequestStep as RequestStepSchema
    from app.schemas.assertion import Assertion as AssertionSchema
    
    steps = db.query(RequestStep).filter(RequestStep.test_case_id == case_id) \
        .order_by(RequestStep.order, RequestStep.id) \
        .all()
    
    result = []
    for step in steps:
        step_dict = RequestStepSchema.model_validate(step).model_dump()
        step_dict["assertions"] = [AssertionSchema.model_validate(a).model_dump() for a in step.assertions]
        result.append(step_dict)
    
    return ResponseModel(data=result)
