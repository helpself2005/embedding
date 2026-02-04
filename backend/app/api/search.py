# -*- coding: utf-8 -*-
import os
import asyncio
import tempfile
import aiofiles
import mimetypes
import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile
from backend.app.schema import ApiResponse, SearchRequest, OneImageUploadDTO, OneImageSearchDTO
from backend.core.errors import *
from backend.app.service.imgsearch import search_image_service
from backend.core.logs.logger import logger
from backend.core.configs.config import settings
from backend.storage.vdb.milvusdb import MilvusDB
from backend.app.api.depends import get_milvus_client

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]
router = APIRouter()
from pydantic import BaseModel
import base64
from typing import List, Optional


# mcp接口测试
@router.post(
    "/search",
    operation_id="search_image",
    summary="搜索图片",
    description=f"图片支持类型:{ALLOWED_EXTENSIONS}",
    response_model=ApiResponse,
)
async def search_image(
    files: SearchRequest, milvus_client: MilvusDB = Depends(get_milvus_client)
) -> ApiResponse:
    tmp_dir = os.path.join(settings.mkdtempdir, "predict")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    try:
        async with aiofiles.open(files.file_data, "rb") as out_file:
            file_data = await out_file.read()
        async with aiofiles.open(
            os.path.join(tmp_dir, files.file_data), "wb"
        ) as out_file:
            await out_file.write(file_data)

        file_type, _ = mimetypes.guess_type(files.file_name)

        one_image_search_dto = OneImageSearchDTO(
            **{
                "file_data": file_data,
                "file_name": files.file_name,
                "file_type": file_type,
                "top_k": files.top_k,
                "cosine": files.cosine,
            }
        )
        search_data = await asyncio.to_thread(
            search_image_service, one_image_search_dto, milvus_client
        )

        return ApiResponse(
            code=MessageCode.SUCCESS, msg=MessageStatus.SUCCESS, data=f"{search_data}"
        )
    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(
            f"code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}"
        )
        return ApiResponse(
            code=MessageCode.FAIL, msg=MessageStatus.FAIL, data=f"{err_msg}"
        )


# 网页图片搜索测试
@router.post(
    "/api_search_image",
    operation_id="api_search_image",
    summary="网页图片搜索测试",
    description=f"图片支持类型:{ALLOWED_EXTENSIONS}",
    response_model=ApiResponse,
)
async def api_search_image(
    files: List[UploadFile] = File(...),
    milvus_client: MilvusDB = Depends(get_milvus_client),
) -> ApiResponse:
    file_status = []
    tmp_dir = os.path.join(settings.mkdtempdir, "predict")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    try:
        for uploaded_file in files:
            logger.info(f"开始解析文件: {uploaded_file.filename}")
            file_extension = os.path.splitext(uploaded_file.filename)[1]
            if file_extension not in ALLOWED_EXTENSIONS:
                resdata = {
                    "filename": uploaded_file.filename,
                    "filestatus": "fail",
                    "fileresult": [],
                }
                file_status.append(resdata)
                continue
            # 创建临时文件
            tmp_file = os.path.join(tmp_dir, uploaded_file.filename)
            # 使用aiofiles模块异步写入文件
            file_data = await uploaded_file.read()
            async with aiofiles.open(tmp_file, "wb") as out_file:
                await out_file.write(file_data)
            one_image_search_dto = OneImageSearchDTO(
                **{
                    "file_data": file_data,
                    "file_name": uploaded_file.filename,
                    "file_type": uploaded_file.content_type,
                    "top_k": 5,
                    "cosine": 0.25,
                }
            )
            search_data = await asyncio.to_thread(
                search_image_service, one_image_search_dto, milvus_client
            )
            # if vectorize_data.get("output", []):
            #     failed_files.append({"filename": uploaded_file.filename})
            file_status.append(
                {
                    "filename": uploaded_file.filename,
                    "filestatus": "success",
                    "fileresult": search_data,
                }
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
