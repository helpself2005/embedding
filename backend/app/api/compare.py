# -*- coding: utf-8 -*-
import os
import asyncio
import aiofiles
import mimetypes
import traceback
from typing import List
from fastapi import APIRouter, File, Form, UploadFile
from backend.app.schema import SearchResponse
from backend.app.schema.imgcompare import ImageCompareDTO, ImageCompareResult
from backend.core.errors import MessageCode, MessageStatus
from backend.app.service.imgcompare import compare_images_service
from backend.core.logs.logger import logger
from backend.core.configs.config import settings

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]
router = APIRouter()


@router.post(
    "/compare",
    operation_id="api_compare_images",
    summary="对比两张图片中的物品是否相同",
    description=f"接收两张图片和一个场景描述，判断图片中的物品是否是同一个。图片支持类型:{ALLOWED_EXTENSIONS}",
    response_model=SearchResponse,
)
async def api_compare_images(
    image1: UploadFile = File(..., description="第一张图片"),
    image2: UploadFile = File(..., description="第二张图片"),
    scene_description: str = Form(..., description="场景描述信息"),
) -> SearchResponse:
    """
    对比两张图片中的物品是否相同
    
    Args:
        image1: 第一张图片文件
        image2: 第二张图片文件
        scene_description: 场景描述信息，用于指导模型判断
        
    Returns:
        SearchResponse: 包含对比结果的响应
    """
    try:
        # 验证文件格式
        image1_extension = os.path.splitext(image1.filename)[1].lower()
        image2_extension = os.path.splitext(image2.filename)[1].lower()
        
        if image1_extension not in ALLOWED_EXTENSIONS:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第一张图片格式不支持，支持的类型: {ALLOWED_EXTENSIONS}",
                data=None
            )
        
        if image2_extension not in ALLOWED_EXTENSIONS:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第二张图片格式不支持，支持的类型: {ALLOWED_EXTENSIONS}",
                data=None
            )
        
        # 读取图片数据
        logger.info(f"开始处理图片对比请求: image1={image1.filename}, image2={image2.filename}, scene={scene_description}")
        
        image1_data = await image1.read()
        image2_data = await image2.read()
        
        # 获取图片MIME类型
        image1_type, _ = mimetypes.guess_type(image1.filename)
        image2_type, _ = mimetypes.guess_type(image2.filename)
        
        # 如果无法识别MIME类型，根据扩展名设置默认值
        if not image1_type:
            if image1_extension in [".jpg", ".jpeg"]:
                image1_type = "image/jpeg"
            elif image1_extension == ".png":
                image1_type = "image/png"
            elif image1_extension == ".bmp":
                image1_type = "image/bmp"
            else:
                image1_type = "image/jpeg"
        
        if not image2_type:
            if image2_extension in [".jpg", ".jpeg"]:
                image2_type = "image/jpeg"
            elif image2_extension == ".png":
                image2_type = "image/png"
            elif image2_extension == ".bmp":
                image2_type = "image/bmp"
            else:
                image2_type = "image/jpeg"
        
        # 构建DTO
        image_compare_dto = ImageCompareDTO(
            image1_data=image1_data,
            image1_name=image1.filename,
            image1_type=image1_type,
            image2_data=image2_data,
            image2_name=image2.filename,
            image2_type=image2_type,
            scene_description=scene_description,
        )
        
        # 调用service层
        compare_result = await asyncio.to_thread(
            compare_images_service, image_compare_dto
        )
        
        # 转换为字典格式返回
        result_data = {
            "is_same": compare_result.is_same,
            "confidence": compare_result.confidence,
            "reason": compare_result.reason,
        }
        
        logger.info(f"图片对比完成: is_same={compare_result.is_same}, confidence={compare_result.confidence}")
        
        return SearchResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=result_data,
        )
        
    except Exception as e:
        err_msg = traceback.format_exc()
        logger.exception(
            f"code:{MessageCode.FAIL}, msg:{MessageStatus.FAIL}, err_msg:{err_msg}"
        )
        return SearchResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=f"{err_msg}",
        )
