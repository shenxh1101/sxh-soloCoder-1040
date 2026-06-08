from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.environment import Environment, EnvironmentVariable
from app.models.project import Project
from app.schemas.environment import (
    EnvironmentCreate, EnvironmentUpdate, Environment as EnvironmentSchema,
    EnvironmentOut, EnvironmentVariableCreate, EnvironmentVariableUpdate,
    EnvironmentVariable as EnvironmentVariableSchema
)
from app.schemas.common import ResponseModel, PageParams, PageResult

router = APIRouter(prefix="/environments", tags=["环境变量管理"])


@router.get("", response_model=ResponseModel[PageResult[EnvironmentOut]])
def get_environments(
    page_params: PageParams = Depends(),
    project_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Environment)
    
    if project_id:
        query = query.filter(Environment.project_id == project_id)
    
    if keyword:
        query = query.filter(Environment.name.contains(keyword) | Environment.description.contains(keyword))
    
    total = query.count()
    items = query.order_by(Environment.is_default.desc(), Environment.id.desc()) \
        .offset((page_params.page - 1) * page_params.page_size) \
        .limit(page_params.page_size) \
        .all()
    
    result_items = []
    for env in items:
        env_dict = EnvironmentSchema.model_validate(env).model_dump()
        env_dict["variables"] = [
            {**v.__dict__, "value": "***" if v.is_secret else v.value}
            for v in env.variables
        ]
        result_items.append(EnvironmentOut(**env_dict))
    
    return ResponseModel(
        data=PageResult(
            items=result_items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=(total + page_params.page_size - 1) // page_params.page_size
        )
    )


@router.get("/{env_id}", response_model=ResponseModel[EnvironmentOut])
def get_environment(env_id: int, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    env_dict = EnvironmentSchema.model_validate(env).model_dump()
    env_dict["variables"] = [
        {**v.__dict__, "value": "***" if v.is_secret else v.value}
        for v in env.variables
    ]
    
    return ResponseModel(data=EnvironmentOut(**env_dict))


@router.post("", response_model=ResponseModel[EnvironmentSchema])
def create_environment(env_in: EnvironmentCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == env_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if env_in.is_default:
        db.query(Environment).filter(
            Environment.project_id == env_in.project_id,
            Environment.is_default == True
        ).update({"is_default": False})
    
    env_data = env_in.model_dump(exclude={"variables"})
    env = Environment(**env_data)
    db.add(env)
    db.flush()
    
    for var_in in env_in.variables or []:
        var = EnvironmentVariable(environment_id=env.id, **var_in.model_dump())
        db.add(var)
    
    db.commit()
    db.refresh(env)
    return ResponseModel(data=env, message="创建成功")


@router.put("/{env_id}", response_model=ResponseModel[EnvironmentSchema])
def update_environment(env_id: int, env_in: EnvironmentUpdate, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    if env_in.is_default and not env.is_default:
        db.query(Environment).filter(
            Environment.project_id == env.project_id,
            Environment.is_default == True,
            Environment.id != env_id
        ).update({"is_default": False})
    
    update_data = env_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(env, key, value)
    
    db.commit()
    db.refresh(env)
    return ResponseModel(data=env, message="更新成功")


@router.delete("/{env_id}", response_model=ResponseModel)
def delete_environment(env_id: int, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    db.delete(env)
    db.commit()
    return ResponseModel(message="删除成功")


@router.post("/{env_id}/variables", response_model=ResponseModel[EnvironmentVariableSchema])
def add_environment_variable(env_id: int, var_in: EnvironmentVariableCreate, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    existing = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.environment_id == env_id,
        EnvironmentVariable.key == var_in.key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="变量名已存在")
    
    var = EnvironmentVariable(environment_id=env_id, **var_in.model_dump())
    db.add(var)
    db.commit()
    db.refresh(var)
    return ResponseModel(data=var, message="添加成功")


@router.put("/variables/{var_id}", response_model=ResponseModel[EnvironmentVariableSchema])
def update_environment_variable(var_id: int, var_in: EnvironmentVariableUpdate, db: Session = Depends(get_db)):
    var = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == var_id).first()
    if not var:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    update_data = var_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(var, key, value)
    
    db.commit()
    db.refresh(var)
    return ResponseModel(data=var, message="更新成功")


@router.delete("/variables/{var_id}", response_model=ResponseModel)
def delete_environment_variable(var_id: int, db: Session = Depends(get_db)):
    var = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == var_id).first()
    if not var:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    db.delete(var)
    db.commit()
    return ResponseModel(message="删除成功")


@router.get("/project/{project_id}/default", response_model=ResponseModel[EnvironmentOut])
def get_default_environment(project_id: int, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(
        Environment.project_id == project_id,
        Environment.is_default == True
    ).first()
    
    if not env:
        env = db.query(Environment).filter(Environment.project_id == project_id).first()
    
    if not env:
        raise HTTPException(status_code=404, detail="该项目暂无环境配置")
    
    env_dict = EnvironmentSchema.model_validate(env).model_dump()
    env_dict["variables"] = [
        {**v.__dict__, "value": "***" if v.is_secret else v.value}
        for v in env.variables
    ]
    
    return ResponseModel(data=EnvironmentOut(**env_dict))
