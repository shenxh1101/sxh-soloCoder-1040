from fastapi import APIRouter

from app.api.v1.project import router as project_router
from app.api.v1.test_suite import router as test_suite_router
from app.api.v1.test_case import router as test_case_router
from app.api.v1.request_step import router as request_step_router
from app.api.v1.assertion import router as assertion_router
from app.api.v1.environment import router as environment_router
from app.api.v1.task import router as task_router
from app.api.v1.execution_record import router as execution_record_router
from app.api.v1.notification import router as notification_router

api_router = APIRouter()

api_router.include_router(project_router)
api_router.include_router(test_suite_router)
api_router.include_router(test_case_router)
api_router.include_router(request_step_router)
api_router.include_router(assertion_router)
api_router.include_router(environment_router)
api_router.include_router(task_router)
api_router.include_router(execution_record_router)
api_router.include_router(notification_router)
