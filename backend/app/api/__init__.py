"""Routers package."""

from fastapi import APIRouter
from .upload import router as upload_router
from .search import router as search_router


# 创建v1版本的路由器
api_router = APIRouter(prefix="/image_search")

# 注册各个功能模块的路由
api_router.include_router(upload_router, prefix="/upload", tags=["图片上传"])
api_router.include_router(search_router, prefix="/search", tags=["图片搜索"])








