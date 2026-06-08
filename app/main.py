from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.v1.router import api_router
from app.core.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="自动化测试后端服务，供业务系统提交接口检查任务并获取结果",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


@app.get("/", tags=["健康检查"])
async def root():
    return {
        "code": 200,
        "message": "success",
        "data": {
            "name": settings.PROJECT_NAME,
            "version": "1.0.0",
            "status": "running"
        }
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "healthy"
        }
    }


app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
