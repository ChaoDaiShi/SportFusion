"""FastAPI 项目入口 - 多元经营体育产业规模测算可视化平台"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging
import traceback

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="体育产业规模测算可视化平台",
    description="多元经营体育产业规模测算与可视化分析系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 全局 CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由模块
from routers import assistant, data_preprocess, enterprise_recognition, output_calc, chart_data, model_validate, chat, monitoring
from api import share, scale, review, system

app.include_router(data_preprocess.router, prefix="/api/data", tags=["数据预处理"])
app.include_router(enterprise_recognition.router, prefix="/api/recognition", tags=["企业识别"])
app.include_router(output_calc.router, prefix="/api/measure", tags=["产值测算"])
app.include_router(chart_data.router, prefix="/api/chart", tags=["图表数据"])
app.include_router(model_validate.router, prefix="/api/validate", tags=["模型校验"])
app.include_router(chat.router, prefix="/api/chat", tags=["智能助手"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["统计监测"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["智能研判"])
app.include_router(share.router, prefix="/api/share", tags=["比重测算"])
app.include_router(scale.router, prefix="/api/scale", tags=["规模测算"])
app.include_router(review.router, prefix="/api/review", tags=["人工复核"])
app.include_router(system.router, prefix="/api/system", tags=["系统管理"])


@app.get("/")
def root():
    return {"message": "体育产业规模测算可视化平台 API", "docs": "/docs"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logging.error(f"全局异常: {str(exc)}")
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "data": None,
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 异常处理器"""
    return JSONResponse(
        status_code=404,
        content={
            "code": 404,
            "message": "请求的资源不存在",
            "data": None,
        },
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """请求参数校验异常处理器"""
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": "请求参数格式错误，请检查输入",
            "data": None,
        },
    )
