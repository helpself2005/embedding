"""
FastAPI应用工厂模块
负责创建和配置FastAPI应用实例
"""
from fastapi import FastAPI

from backend.core.configs.config import settings

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
        title=settings.app_name,
        description=settings.app_desc,
        docs_url="/api/docs",
        redoc_url="/api/redocs",
        openapi_url="/api/openapi.json",  # 必须设置，否则文档页面无法加载
        version=settings.app_version,
        lifespan=lifespan,
    )
    

    # 配置中间件
    configure_middleware(app)
    

    # 注册API路由
    app.include_router(api_router, prefix="/api")
    return app
