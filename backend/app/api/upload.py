# -*- coding: utf-8 -*-
import os
import asyncio
import tempfile
import aiofiles
import mimetypes
import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from backend.app.schema import *
from backend.core.errors import *
from backend.core.logs.logger import logger
from backend.core.configs.config import settings
from backend.storage.vdb.milvusdb import MilvusDB
from backend.app.api.depends import get_milvus_client
from backend.app.service.imginsert import insert_image_service

ALLOWED_EXTENSIONS = [".jpg",".jpeg",".png",".bmp"]

router = APIRouter()

# mcp接口测试
@router.post("/upload_image", operation_id="upload_image", summary="上传图片", description=f"图片支持类型:{ALLOWED_EXTENSIONS}")
async def upload_image(files:UploadRequest,
    milvus_client:MilvusDB = Depends(get_milvus_client)):
    try:
        tmp_dir = os.path.join(settings.mkdtempdir, files.file_class)
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        async with aiofiles.open(files.file_data, 'rb') as out_file:
            file_data = await out_file.read()
        async with aiofiles.open(os.path.join(tmp_dir, files.file_data), 'wb') as out_file:
            await out_file.write(file_data) 

        file_type, _ = mimetypes.guess_type(files.file_name)
     
        one_image_upload_dto = OneImageUploadDTO(**{"file_data":file_data, "file_name":files.file_name, "file_type": file_type,  "file_class": files.file_class})    
        vectorize_data = await asyncio.to_thread(insert_image_service, one_image_upload_dto, milvus_client)

        return SearchResponse(code=MessageCode.SUCCESS, msg=MessageStatus.SUCCESS, data=f"{vectorize_data}")

    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(f'code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}')
        return SearchResponse(code=MessageCode.FAIL, msg=MessageStatus.FAIL, data=f"{err_msg}")



# 网页上传图片测试
@router.post("/api_upload_image", operation_id="api_upload_image", summary="网页上传图片测试", description=f"图片支持类型:{ALLOWED_EXTENSIONS}")
async def api_upload_image(files: List[UploadFile] = File(...), categories: Optional[List[str]] = Form(None),
    milvus_client:MilvusDB = Depends(get_milvus_client)):
    file_status = []
    try:
        for uploaded_file, file_class in zip(files, categories):
            tmp_dir = os.path.join(settings.mkdtempdir, file_class)
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            
            logger.info(f"开始解析文件: {uploaded_file.filename}")
            file_extension = os.path.splitext(uploaded_file.filename)[1]
            if file_extension not in ALLOWED_EXTENSIONS:
                resdata = {"filename": uploaded_file.filename, "filestatus": "fail"}
                file_status.append(resdata)
                continue
            # 创建临时文件
            tmp_file = os.path.join(tmp_dir, uploaded_file.filename)
            # 使用aiofiles模块异步写入文件
            file_data = await uploaded_file.read()
            async with aiofiles.open(tmp_file, 'wb') as out_file:
                await out_file.write(file_data)
            one_image_upload_dto = OneImageUploadDTO(**{"file_data":file_data, "file_name":uploaded_file.filename, "file_type": uploaded_file.content_type,  "file_class": file_class})    
            vectorize_data = await asyncio.to_thread(insert_image_service, one_image_upload_dto, milvus_client)
            # if vectorize_data.get("output", []):
            #     file_status.append({"filename": uploaded_file.filename, "filestatus": "fail"})
            file_status.append({"filename": uploaded_file.filename, "filestatus": "success"})
        return SearchResponse(code=MessageCode.SUCCESS, msg=MessageStatus.SUCCESS, data=f"{file_status}")

    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(f'code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}')
        return SearchResponse(code=MessageCode.FAIL, msg=MessageStatus.FAIL, data=f"{err_msg}")
    


    