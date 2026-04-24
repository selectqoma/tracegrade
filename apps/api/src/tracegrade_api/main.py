import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import close_clickhouse, close_redis, get_clickhouse, init_clickhouse, init_redis
from .ingest.buffer import SpanBuffer
from .ingest.router import router as ingest_router
from .routes.sessions import router as sessions_router
from .routes.annotations import router as annotations_router
from .routes.traces import router as traces_router
from .routes.evals import router as evals_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TraceGrade API")
    await init_clickhouse()
    await init_redis()

    buffer = SpanBuffer(
        clickhouse_client=get_clickhouse(),
        batch_size=settings.INGEST_BATCH_SIZE,
        flush_interval=settings.INGEST_FLUSH_INTERVAL,
    )
    buffer.start()
    app.state.span_buffer = buffer

    yield

    await buffer.stop()
    await close_clickhouse()
    await close_redis()
    logger.info("TraceGrade API shutdown complete")


app = FastAPI(
    title="TraceGrade",
    description="Turn production AI agent failures into regression tests",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(sessions_router)
app.include_router(annotations_router)
app.include_router(traces_router)
app.include_router(evals_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
