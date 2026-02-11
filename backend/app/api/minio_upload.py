# -*- coding: utf-8 -*-
"""
MinIO 文件上传接口模块
"""
import os
import traceback
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, File, Form, UploadFile
from backend.app.schema import ApiResponse
from backend.core.errors import MessageCode, MessageStatus
from backend.core.logs.logger import logger
from backend.storage.minio_client import get_minio_client
from backend.utils.stringutils import sanitize_folder_name, sanitize_filename

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]

router = APIRouter()


@router.post(
    "/api_upload_to_minio",
    operation_id="api_upload_to_minio",
    summary="上传文件到 MinIO",
    description=f"上传文件到 MinIO 对象存储，返回文件访问路径。支持的文件类型:{ALLOWED_EXTENSIONS}",
    response_model=ApiResponse,
)
async def api_upload_to_minio(
    files: List[UploadFile] = File(...),
    folder: Optional[str] = Form(None, description="文件存储文件夹路径（可选）"),
) -> ApiResponse:
    """
    上传文件到 MinIO 对象存储
    
    Args:
        files: 要上传的文件列表
        folder: 文件存储的文件夹路径（可选），例如 "images/2024/01"
        
    Returns:
        ApiResponse: 包含上传结果和文件访问路径的响应
    """
    upload_results = []
    
    try:
        minio_client = get_minio_client()
        
        for uploaded_file in files:
            try:
                logger.info(f"开始上传文件到 MinIO: {uploaded_file.filename}")
                
                # 验证文件格式
                file_extension = os.path.splitext(uploaded_file.filename)[1].lower()
                if file_extension not in ALLOWED_EXTENSIONS:
                    upload_results.append({
                        "filename": uploaded_file.filename,
                        "status": "fail",
                        "error": f"不支持的文件格式: {file_extension}，支持的类型: {ALLOWED_EXTENSIONS}",
                        "url": None,
                    })
                    continue
                
                # 读取文件数据
                file_data = await uploaded_file.read()
                
                # 生成对象名称（文件路径）
                # 格式: folder/yyyy-MM-dd/uuid-filename
                # 将中文文件夹路径和文件名转换为英文
                if folder:
                    folder_path_raw = folder.strip("/")  # 移除首尾斜杠
                    # 处理多层路径：对每一层文件夹名称进行清理
                    folder_parts = folder_path_raw.split("/")
                    sanitized_parts = [sanitize_folder_name(part) for part in folder_parts]
                    folder_path = "/".join(sanitized_parts)
                else:
                    folder_path = "uploads"
                
                # 添加日期文件夹
                date_folder = datetime.now().strftime("%Y-%m-%d")
                
                # 生成唯一文件名（避免文件名冲突）
                file_uuid = str(uuid.uuid4())[:8]
                sanitized_filename = sanitize_filename(uploaded_file.filename)
                object_name = f"{folder_path}/{date_folder}/{file_uuid}-{sanitized_filename}"
                
                # 上传到 MinIO
                file_url = minio_client.upload_file(
                    file_data=file_data,
                    object_name=object_name,
                    content_type=uploaded_file.content_type,
                )
                
                upload_results.append({
                    "filename": uploaded_file.filename,
                    "status": "success",
                    "object_name": object_name,
                    "url": file_url,
                    "size": len(file_data),
                })
                
                logger.info(f"文件上传成功: {uploaded_file.filename} -> {file_url}")
                
            except Exception as e:
                err_msg = str(e)
                logger.error(f"上传文件失败: {uploaded_file.filename}, 错误: {err_msg}")
                upload_results.append({
                    "filename": uploaded_file.filename,
                    "status": "fail",
                    "error": err_msg,
                    "url": None,
                })
        
        return ApiResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=upload_results,
        )
        
    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(
            f"code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}"
        )
        return ApiResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=f"{err_msg}",
        )
