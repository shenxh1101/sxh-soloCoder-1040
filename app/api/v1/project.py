from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, Project as ProjectSchema
from app.schemas.common import ResponseModel, PageParams, PageResult

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.get("", response_model=ResponseModel[PageResult[ProjectSchema]])
def get_projects(
    page_params: PageParams = Depends(),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Project)
    
    if keyword:
        query = query.filter(Project.name.contains(keyword) | Project.description.contains(keyword))
    
    total = query.count()
    items = query.order_by(Project.id.desc()) \
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


@router.get("/{project_id}", response_model=ResponseModel[ProjectSchema])
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ResponseModel(data=project)


@router.post("", response_model=ResponseModel[ProjectSchema])
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**project_in.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return ResponseModel(data=project, message="创建成功")


@router.put("/{project_id}", response_model=ResponseModel[ProjectSchema])
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    for key, value in project_in.model_dump().items():
        setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return ResponseModel(data=project, message="更新成功")


@router.delete("/{project_id}", response_model=ResponseModel)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    db.delete(project)
    db.commit()
    return ResponseModel(message="删除成功")


@router.get("/{project_id}/stats", response_model=ResponseModel)
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    from app.models.test_suite import TestSuite
    from app.models.test_case import TestCase
    from app.models.execution_record import ExecutionRecord
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    suite_count = db.query(TestSuite).filter(TestSuite.project_id == project_id).count()
    case_count = db.query(TestCase).join(TestSuite).filter(TestSuite.project_id == project_id).count()
    execution_count = db.query(ExecutionRecord).filter(ExecutionRecord.project_id == project_id).count()
    
    recent_executions = db.query(ExecutionRecord) \
        .filter(ExecutionRecord.project_id == project_id) \
        .order_by(ExecutionRecord.id.desc()) \
        .limit(10) \
        .all()
    
    pass_rates = [e.pass_rate for e in recent_executions if e.status == "completed"]
    avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0
    
    return ResponseModel(data={
        "project_id": project_id,
        "suite_count": suite_count,
        "case_count": case_count,
        "execution_count": execution_count,
        "avg_pass_rate": round(avg_pass_rate, 2),
        "recent_executions": len(recent_executions)
    })
