import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.routes import router
from src.config import get_settings
from src.database import get_db
from src.observability import configure_logging, logger, request_id_var
from src.services import vectorstore
from src.services.alerts import get_alert_service
from src.services.chroma_seed import ensure_seeded
from src.services.tracing import configure_tracing

# Thông điệp cố định cho MỌI lỗi 500 — không bao giờ lộ nội dung exception ra
# response (chuỗi kết nối DB Supabase có mật khẩu nằm trong message của
# OperationalError). Chi tiết thật chỉ nằm trong log server, kèm request_id
# để tra cứu.
UNHANDLED_ERROR_MESSAGE = "Đã có lỗi xảy ra, vui lòng thử lại sau."


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")

    # `metrics_token` mặc định rỗng để máy dev chạy được ngay (xem config.py).
    # Đánh đổi là có thể quên đặt khi lên production — la lên ở đây để nó không
    # quên được trong im lặng. Chỉ cảnh báo, KHÔNG chặn khởi động: /metrics mở
    # là rò rỉ số liệu vận hành, còn service không lên là hỏng cả sản phẩm.
    if settings.app_env == "production" and not settings.metrics_token:
        logger.warning(
            "metrics_endpoint_unprotected",
            extra={"hint": "APP_ENV=production nhưng METRICS_TOKEN rỗng — "
                           "/api/v1/metrics đang mở cho mọi người"},
        )

    ensure_seeded(get_settings().chroma_persist_dir, "./data/chroma_seed")
    yield
    print("Shutting down...")


settings = get_settings()
configure_logging(settings.log_level)
# Trước khi FastAPI dựng app: LangChain đọc cấu hình tracing lúc gọi LLM, nên
# chỉ cần environ đã đúng trước request đầu tiên (V1, deliverable #4 của BTC).
configure_tracing(settings)

app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Gắn `request_id` cho mỗi request (V5) + ghi một dòng log khi xong.

    `status_code` mặc định 500: nếu `call_next` ném exception chưa bắt,
    khối `finally` vẫn chạy trước khi exception lan lên
    `unhandled_exception_handler` (đăng ký bên dưới) — 500 là kết quả cuối
    cùng người dùng nhận được trong trường hợp đó.
    """
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        # Record metrics for alerting & Prometheus
        alerts = get_alert_service()
        alerts.record_request(status_code)
        alerts.record_latency(duration_ms)
        alerts.check_and_alert()
        request_id_var.reset(token)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Bắt lỗi tập trung (V9): trả 500 cố định, không lộ nội dung exception.

    `request.state.request_id` chứ không phải contextvar `request_id_var`:
    middleware ở trên đã `reset()` contextvar trong `finally` trước khi
    exception lan tới đây, nên contextvar lúc này đã về giá trị mặc định.
    """
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("unhandled_exception", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={"message": UNHANDLED_ERROR_MESSAGE, "request_id": request_id},
        headers={"X-Request-Id": request_id},
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

    # Record health for alerting
    get_alert_service().record_health_check(healthy)

    return JSONResponse(report, status_code=200 if healthy else 503)
