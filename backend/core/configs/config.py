# -*- coding: utf-8 -*-
"""
配置文件模块
负责管理应用的所有配置项
"""
import os
from pathlib import Path
from typing import Literal, Optional
from backend.core.logs.logger import logger

# import logging as logger
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 计算项目根目录路径
def get_project_root():
    """获取项目根目录路径"""
    current_file = Path(__file__)
    # 从 backend/core/configs/config.py 向上查找项目根目录
    # 项目根目录应该包含 .env 文件
    for parent in [current_file.parent] + list(current_file.parents):
        if (parent / ".env").exists():
            return str(parent)
    # 如果没找到，返回当前工作目录
    return os.getcwd()


CONFIG_DIR = get_project_root()

LOG_LEVEL = Literal[
    "NOTSET",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "FATAL",
]

ENVIRONMENT = Literal[
    "development",
    "production",
]


ENV_FILE = f"{CONFIG_DIR}/.env"
if os.path.exists(ENV_FILE):
    logger.info(f"环境配置文件加载成功: {ENV_FILE}")
    logger.info(f"找到 .env 文件: {ENV_FILE}")
    pass
else:
    logger.info(f"未找到 .env 文件: {ENV_FILE}")
    # 尝试其他可能的路径
    alternative_paths = [
        ".env",  # 当前工作目录
        os.path.join(os.getcwd(), ".env"),  # 绝对路径
    ]
    for alt_path in alternative_paths:
        if os.path.exists(alt_path):
            ENV_FILE = alt_path
            logger.info(f"使用备选环境配置文件: {ENV_FILE}")
            break


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    # 应用相关配置
    app_name: str = Field("图像处理", env="APP_NAME")
    app_desc: str = Field("图像处理程序", env="APP_DESC")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8080, env="PORT")
    workers: int = Field(1, env="WORKERS")
    environment: str = Field(
        "development", env="ENVIRONMENT"
    )  # 默认设置为 "development", 生产环境为 "production"

    mkdtempdir: str = Field(
        "/Users/plshi/Documents/image_search/tempdir", env="MKDTEMPDIR"
    )

    embedding_provider: str = Field("dashscope", env="EMBEDDING_PROVIDER")

    dashscope_embedding_api_key: str = Field(
        "sk-bbc64eaa6c7d4fc4a15df033554d2d5c", env="DASHSCOPE_EMBEDDING_API_KEY"
    )

    dashscope_embedding_dims: int = Field(1152, env="DASHSCOPE_EMBEDDING_DIMS")

    dashscope_embedding_model: str = Field(
        "tongyi-embedding-vision-plus", env="DASHSCOPE_EMBEDDING_MODEL"
    )

    dashscope_vl_model: str = Field(
        "qwen3-vl-flash", env="DASHSCOPE_VL_MODEL"
    )

    # Milvus配置
    milvus_host: Optional[str] = Field(default="101.42.31.155", env="MILVUS_HOST")
    milvus_port: Optional[str] = Field(default="29530", env="MILVUS_PORT")
    milvus_username: Optional[str] = Field(default=None, env="MILVUS_USERNAME")
    milvus_password: Optional[str] = Field(default=None, env="MILVUS_PASSWORD")
    milvus_collection_name: Optional[str] = Field(
        default="imagesearch", env="MILVUS_COLLECTION_NAME"
    )
    milvus_vector_dim: Optional[int] = Field(default=1152, env="MILVUS_VECTOR_DIM")
    milvus_auto_id: Optional[bool] = Field(default=True, env="MILVUS_AUPO_ID")

    # MinIO配置
    minio_endpoint: Optional[str] = Field(default="101.42.31.155:9000", env="MINIO_ENDPOINT")
    minio_access_key: Optional[str] = Field(default=None, env="MINIO_ACCESS_KEY")
    minio_secret_key: Optional[str] = Field(default=None, env="MINIO_SECRET_KEY")
    minio_secure: Optional[bool] = Field(default=False, env="MINIO_SECURE")  # 是否使用HTTPS
    minio_bucket_name: Optional[str] = Field(default="images", env="MINIO_BUCKET_NAME")
    minio_region: Optional[str] = Field(default=None, env="MINIO_REGION")

    def __init__(self):
        """初始化配置"""
        # Nacos 配置已在 lifespan 中初始化，这里直接调用父类初始化
        super().__init__()

    @model_validator(mode="before")
    @classmethod
    def empty_strings_to_none(cls, values):
        """将所有字符串字段的空字符串或空白字符串转为 None"""
        for k, v in values.items():
            if isinstance(v, str) and v.strip() == "":
                values[k] = None
        return values


# print('开始打印环境变量')  # 注释掉调试代码
# for key, value in os.environ.items():
#     print(f"{key}: {value}")
settings = Settings()
logger.info(f"settings: {settings}")
