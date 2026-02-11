# -*- coding: utf-8 -*-
import os
import asyncio
import tempfile
import aiofiles
import mimetypes
import traceback
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from backend.app.schema import ApiResponse, UploadRequest, OneImageUploadDTO
from backend.core.errors import *
from backend.core.logs.logger import logger
from backend.core.configs.config import settings
from backend.storage.milvus_client import MilvusDB
from backend.storage.minio_client import get_minio_client
from backend.app.api.depends import get_milvus_client
from backend.app.service.imginsert import insert_image_service
from backend.utils.stringutils import sanitize_folder_name, sanitize_filename

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]

router = APIRouter()


# mcp接口测试
@router.post(
    "/local_upload",
    operation_id="upload_image",
    summary="本地上传图片",
    description=f"图片支持类型:{ALLOWED_EXTENSIONS}",
)
async def upload_image(
    files: UploadRequest, milvus_client: MilvusDB = Depends(get_milvus_client)
):
    try:
        tmp_dir = os.path.join(settings.mkdtempdir, files.file_class)
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        async with aiofiles.open(files.file_data, "rb") as out_file:
            file_data = await out_file.read()
        async with aiofiles.open(
            os.path.join(tmp_dir, files.file_data), "wb"
        ) as out_file:
            await out_file.write(file_data)

        file_type, _ = mimetypes.guess_type(files.file_name)

        one_image_upload_dto = OneImageUploadDTO(
            **{
                "file_data": file_data,
                "file_name": files.file_name,
                "file_type": file_type,
                "file_class": files.file_class,
            }
        )
        vectorize_data = await asyncio.to_thread(
            insert_image_service, one_image_upload_dto, milvus_client
        )

        return ApiResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=f"{vectorize_data}",
        )

    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(
            f"code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}"
        )
        return ApiResponse(
            code=MessageCode.FAIL, msg=MessageStatus.FAIL, data=f"{err_msg}"
        )


# 网页上传图片测试
@router.post(
    "/api_upload_image",
    operation_id="api_upload_image",
    summary="网页上传图片测试",
    description=f"图片支持类型:{ALLOWED_EXTENSIONS}",
)
async def api_upload_image(
    files: List[UploadFile] = File(...),
    categories: Optional[List[str]] = Form(None),
    descriptions: Optional[List[str]] = Form(None),
    milvus_client: MilvusDB = Depends(get_milvus_client),
):
    file_status = []
    try:
        minio_client = get_minio_client()
        
        for uploaded_file, file_category, file_description in zip(files, categories, descriptions):
            tmp_dir = os.path.join(settings.mkdtempdir, file_category)
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)

            logger.info(f"开始解析文件: {uploaded_file.filename}")
            file_extension = os.path.splitext(uploaded_file.filename)[1]
            if file_extension not in ALLOWED_EXTENSIONS:
                resdata = {"filename": uploaded_file.filename, "filestatus": "fail"}
                file_status.append(resdata)
                continue
            # 使用aiofiles模块异步读取文件
            file_data = await uploaded_file.read()
            
            # 先上传到 MinIO
            try:
                # 生成对象名称（文件路径）：分类文件夹/日期/uuid-文件名
                # 将中文分类名和文件名转换为英文
                folder_path = sanitize_folder_name(file_category or "uploads")
                date_folder = datetime.now().strftime("%Y-%m-%d")
                file_uuid = str(uuid.uuid4())[:8]
                sanitized_filename = sanitize_filename(uploaded_file.filename)
                object_name = f"{folder_path}/{date_folder}/{file_uuid}-{sanitized_filename}"
                
                # 上传到 MinIO 并获取文件访问地址
                file_url = minio_client.upload_file(
                    file_data=file_data,
                    object_name=object_name,
                    content_type=uploaded_file.content_type,
                )
                logger.info(f"文件已上传到 MinIO: {uploaded_file.filename} -> {file_url}")
            except Exception as minio_error:
                logger.error(f"MinIO 上传失败: {uploaded_file.filename}, 错误: {minio_error}")
                file_url = ""  # 如果 MinIO 上传失败，file_url 为空字符串
            
            # 创建临时文件（保留原有逻辑，用于本地备份）
            tmp_file = os.path.join(tmp_dir, uploaded_file.filename)
            async with aiofiles.open(tmp_file, "wb") as out_file:
                await out_file.write(file_data)
            
            one_image_upload_dto = OneImageUploadDTO(
                **{
                    "file_data": file_data,
                    "file_name": uploaded_file.filename,
                    "file_type": uploaded_file.content_type,
                    "file_class": file_category,
                    "file_description": file_description,  # 文件描述信息
                    "file_url": file_url,  # 设置 MinIO 返回的文件访问地址
                }
            )
            vectorize_data = await asyncio.to_thread(
                insert_image_service, one_image_upload_dto, milvus_client
            )
            # if vectorize_data.get("output", []):
            #     file_status.append({"filename": uploaded_file.filename, "filestatus": "fail"})
            file_status.append(
                {"filename": uploaded_file.filename, "file_url": file_url, "vectorize_data": vectorize_data}
            )
        return ApiResponse(
            code=MessageCode.SUCCESS, msg=MessageStatus.SUCCESS, data=f"{file_status}"
        )

    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(
            f"code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}"
        )
        return ApiResponse(
            code=MessageCode.FAIL, msg=MessageStatus.FAIL, data=f"{err_msg}"
        )
