from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.routes import router
from src.config import get_settings
from src.database import get_db
from src.services import vectorstore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    print("Shutting down...")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/deep")
async def health_deep(db: Session = Depends(get_db)) -> JSONResponse:
    """Kiểm thành phần thật, không chỉ kiểm tiến trình còn sống.

    Tiền lệ 11/08: index Chroma hỏng mà mọi chỉ báo vẫn xanh suốt nhiều giờ.
    Từ khi Chroma nằm trên volume có thể rỗng, `count() == 0` là chế độ hỏng
    NGHIÊM TRỌNG chứ không phải trạng thái hợp lệ: retrieve rỗng khiến guard
    chống bịa từ chối mọi câu hỏi, và không màn hình nào báo lỗi.
    """
    report: dict[str, Any] = {}
    healthy = True

    try:
        db.execute(text("SELECT 1"))
        report["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — báo cáo mọi lỗi hạ tầng
        report["database"] = f"error: {type(exc).__name__}"
        healthy = False

    try:
        count = vectorstore.get_vectorstore()._collection.count()
        report["chroma"] = {"status": "ok" if count else "empty", "documents": count}
        healthy = healthy and count > 0
    except Exception as exc:  # noqa: BLE001
        report["chroma"] = {"status": f"error: {type(exc).__name__}"}
        healthy = False

    return JSONResponse(report, status_code=200 if healthy else 503)
