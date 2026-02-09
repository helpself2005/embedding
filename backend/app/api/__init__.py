"""Routers package."""

from fastapi import APIRouter
from .upload import router as upload_router
from .search import router as search_router
from .compare import router as compare_router
from .minio_upload import router as minio_upload_router
from .local_compare import router as local_compare_router


# 创建v1版本的路由器
api_router = APIRouter(prefix="/image")

# 注册各个功能模块的路由
api_router.include_router(upload_router, tags=["图片上传"])
api_router.include_router(search_router,  tags=["图片搜索"])
api_router.include_router(compare_router, tags=["图片对比"])
api_router.include_router(minio_upload_router, tags=["MinIO文件上传"])
api_router.include_router(local_compare_router, tags=["本地文件对比"])








