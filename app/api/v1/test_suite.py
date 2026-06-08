from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.models.project import Project
from app.schemas.test_suite import TestSuiteCreate, TestSuiteUpdate, TestSuite as TestSuiteSchema, TestSuiteWithStats
from app.schemas.common import ResponseModel, PageParams, PageResult

router = APIRouter(prefix="/test-suites", tags=["测试套件管理"])


@router.get("", response_model=ResponseModel[PageResult[TestSuiteWithStats]])
def get_test_suites(
    page_params: PageParams = Depends(),
    project_id: Optional[int] = None,
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        TestSuite,
        func.count(TestCase.id).label("case_count")
    ).outerjoin(TestCase, TestSuite.id == TestCase.test_suite_id)
    
    if project_id:
        query = query.filter(TestSuite.project_id == project_id)
    
    if keyword:
        query = query.filter(TestSuite.name.contains(keyword) | TestSuite.description.contains(keyword))
    
    if tag:
        query = query.filter(TestSuite.tags.contains([tag]))
    
    query = query.group_by(TestSuite.id)
    
    total = query.count()
    results = query.order_by(TestSuite.id.desc()) \
        .offset((page_params.page - 1) * page_params.page_size) \
        .limit(page_params.page_size) \
        .all()
    
    items = []
    for suite, case_count in results:
        suite_dict = TestSuiteSchema.model_validate(suite).model_dump()
        suite_dict["case_count"] = case_count
        items.append(TestSuiteWithStats(**suite_dict))
    
    return ResponseModel(
        data=PageResult(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=(total + page_params.page_size - 1) // page_params.page_size
        )
    )


@router.get("/{suite_id}", response_model=ResponseModel[TestSuiteWithStats])
def get_test_suite(suite_id: int, db: Session = Depends(get_db)):
    result = db.query(
        TestSuite,
        func.count(TestCase.id).label("case_count")
    ).outerjoin(TestCase, TestSuite.id == TestCase.test_suite_id) \
     .filter(TestSuite.id == suite_id) \
     .group_by(TestSuite.id) \
     .first()
    
    if not result:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    
    suite, case_count = result
    suite_dict = TestSuiteSchema.model_validate(suite).model_dump()
    suite_dict["case_count"] = case_count
    
    return ResponseModel(data=TestSuiteWithStats(**suite_dict))


@router.post("", response_model=ResponseModel[TestSuiteSchema])
def create_test_suite(suite_in: TestSuiteCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == suite_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    suite = TestSuite(**suite_in.model_dump())
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return ResponseModel(data=suite, message="创建成功")


@router.put("/{suite_id}", response_model=ResponseModel[TestSuiteSchema])
def update_test_suite(suite_id: int, suite_in: TestSuiteUpdate, db: Session = Depends(get_db)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    
    update_data = suite_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(suite, key, value)
    
    db.commit()
    db.refresh(suite)
    return ResponseModel(data=suite, message="更新成功")


@router.delete("/{suite_id}", response_model=ResponseModel)
def delete_test_suite(suite_id: int, db: Session = Depends(get_db)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    
    db.delete(suite)
    db.commit()
    return ResponseModel(message="删除成功")


@router.get("/{suite_id}/cases", response_model=ResponseModel[List])
def get_suite_cases(suite_id: int, db: Session = Depends(get_db)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    
    from app.schemas.test_case import TestCaseWithSteps
    
    cases = db.query(TestCase).filter(TestCase.test_suite_id == suite_id) \
        .order_by(TestCase.order, TestCase.id) \
        .all()
    
    result = []
    for case in cases:
        case_dict = TestCaseWithSteps.model_validate(case).model_dump()
        case_dict["step_count"] = len(case.request_steps)
        result.append(case_dict)
    
    return ResponseModel(data=result)
