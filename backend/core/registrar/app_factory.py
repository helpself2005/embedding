"""
FastAPI应用工厂模块
负责创建和配置FastAPI应用实例
"""
from fastapi import FastAPI

from .lifespan import lifespan
from backend.app.api import api_router
from .middleware import configure_middleware


def create_app() -> FastAPI:
    """
    创建并配置FastAPI应用实例
    
    Returns:
        FastAPI: 配置完成的FastAPI应用实例
    """
    # 创建FastAPI应用
    app = FastAPI(
        title="以图搜图",
        description="基于FastAPI的图片搜索",
        docs_url="/api/docs",
        redoc_url="/api/redocs",
        version="1.0.0",
        lifespan=lifespan,
    )
    

    # 配置中间件
    configure_middleware(app)
    

    # 注册API路由
    app.include_router(api_router, prefix="/api")
    return app
