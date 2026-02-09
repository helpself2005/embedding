# -*- coding: utf-8 -*-
"""
MinIO 客户端封装模块
"""
from minio import Minio
from minio.error import S3Error
from backend.core.configs.config import settings
from backend.core.logs.logger import logger
from typing import Optional
import os


class MinIOClient:
    """MinIO 客户端封装类"""
    
    def __init__(self):
        """初始化 MinIO 客户端"""
        try:
            self.client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
                region=settings.minio_region,
            )
            self.bucket_name = settings.minio_bucket_name
            self._ensure_bucket_exists()
            logger.info(f"MinIO 客户端初始化成功: endpoint={settings.minio_endpoint}, bucket={self.bucket_name}")
        except Exception as e:
            logger.error(f"MinIO 客户端初始化失败: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在，如果不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"创建 MinIO 存储桶: {self.bucket_name}")
            else:
                logger.info(f"MinIO 存储桶已存在: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"MinIO 存储桶操作失败: {e}")
            raise
    
    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> str:
        """
        上传文件到 MinIO
        
        Args:
            file_data: 文件二进制数据
            object_name: 对象名称（文件路径）
            content_type: 文件 MIME 类型
            bucket_name: 存储桶名称，如果为 None 则使用默认存储桶
            
        Returns:
            str: 文件的访问 URL
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 确保存储桶存在
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"创建存储桶: {bucket}")
            
            # 上传文件
            from io import BytesIO
            file_stream = BytesIO(file_data)
            
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=file_stream,
                length=len(file_data),
                content_type=content_type or "application/octet-stream",
            )
            
            # 生成访问 URL
            if settings.minio_secure:
                protocol = "https"
            else:
                protocol = "http"
            
            url = f"{protocol}://{settings.minio_endpoint}/{bucket}/{object_name}"
            
            logger.info(f"文件上传成功: bucket={bucket}, object={object_name}, url={url}")
            return url
            
        except S3Error as e:
            logger.error(f"MinIO 上传文件失败: {e}")
            raise
        except Exception as e:
            logger.error(f"上传文件时发生未知错误: {e}")
            raise
    
    def get_file_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: int = 7 * 24 * 60 * 60,  # 默认7天过期
    ) -> str:
        """
        获取文件的预签名 URL（临时访问链接）
        
        Args:
            object_name: 对象名称（文件路径）
            bucket_name: 存储桶名称，如果为 None 则使用默认存储桶
            expires: URL 过期时间（秒），默认7天
            
        Returns:
            str: 预签名 URL
        """
        try:
            from urllib.parse import urlencode
            
            bucket = bucket_name or self.bucket_name
            url = self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=expires,
            )
            logger.info(f"生成预签名 URL: bucket={bucket}, object={object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"生成预签名 URL 失败: {e}")
            raise
    
    def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        删除文件
        
        Args:
            object_name: 对象名称（文件路径）
            bucket_name: 存储桶名称，如果为 None 则使用默认存储桶
            
        Returns:
            bool: 是否删除成功
        """
        try:
            bucket = bucket_name or self.bucket_name
            self.client.remove_object(bucket_name=bucket, object_name=object_name)
            logger.info(f"删除文件成功: bucket={bucket}, object={object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"删除文件失败: {e}")
            return False


# 全局 MinIO 客户端实例
_minio_client: Optional[MinIOClient] = None


def get_minio_client() -> MinIOClient:
    """获取 MinIO 客户端实例（单例模式）"""
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClient()
    return _minio_client
