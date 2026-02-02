# -*- coding: utf-8 -*-
import os
import asyncio
import aiofiles
import mimetypes
import traceback
import base64
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, File, Form, UploadFile
from backend.app.schema import SearchResponse
from backend.app.schema.imgcompare import ImageCompareDTO, ImageCompareResult, ImageCompareByURLDTO
from backend.core.errors import MessageCode, MessageStatus
from backend.app.service.imgcompare import compare_images_service, compare_images_by_url_service
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


@router.post(
    "/compare_by_path",
    operation_id="api_compare_images_by_path",
    summary="对比两张图片中的物品是否相同（通过文件路径）",
    description=f"MCP 工具专用接口，接受文件路径字符串。图片支持类型:{ALLOWED_EXTENSIONS}",
    response_model=SearchResponse,
)
async def api_compare_images_by_path(
    image1_path: str = Form(..., description="第一张图片的文件路径"),
    image2_path: str = Form(..., description="第二张图片的文件路径"),
    scene_description: str = Form(..., description="场景描述信息"),
) -> SearchResponse:
    """
    对比两张图片中的物品是否相同（MCP 工具专用接口）
    
    此接口专门为 MCP 工具调用设计，接受文件路径字符串而不是文件对象。
    
    Args:
        image1_path: 第一张图片的文件路径
        image2_path: 第二张图片的文件路径
        scene_description: 场景描述信息，用于指导模型判断
        
    Returns:
        SearchResponse: 包含对比结果的响应
    """
    try:
        # 验证文件路径是否存在
        if not os.path.exists(image1_path):
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第一张图片文件不存在: {image1_path}",
                data=None
            )
        
        if not os.path.exists(image2_path):
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第二张图片文件不存在: {image2_path}",
                data=None
            )
        
        # 验证文件格式
        image1_extension = os.path.splitext(image1_path)[1].lower()
        image2_extension = os.path.splitext(image2_path)[1].lower()
        
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
        logger.info(f"开始处理图片对比请求（文件路径）: image1={image1_path}, image2={image2_path}, scene={scene_description}")
        
        async with aiofiles.open(image1_path, "rb") as f1, aiofiles.open(image2_path, "rb") as f2:
            image1_data = await f1.read()
            image2_data = await f2.read()
        
        # 获取文件名和MIME类型
        image1_filename = os.path.basename(image1_path)
        image2_filename = os.path.basename(image2_path)
        
        image1_type, _ = mimetypes.guess_type(image1_path)
        image2_type, _ = mimetypes.guess_type(image2_path)
        
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
            image1_name=image1_filename,
            image1_type=image1_type,
            image2_data=image2_data,
            image2_name=image2_filename,
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
        
        logger.info(f"图片对比完成（文件路径）: is_same={compare_result.is_same}, confidence={compare_result.confidence}")
        
        return SearchResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=result_data,
        )
        
    except FileNotFoundError as e:
        err_msg = f"文件未找到: {str(e)}"
        logger.error(err_msg)
        return SearchResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=err_msg,
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


def decode_base64_image(base64_str: str) -> tuple[bytes, str]:
    """
    解码 base64 图片字符串
    
    Args:
        base64_str: base64 编码的图片字符串，可以是纯 base64 或 data URL 格式
        
    Returns:
        tuple: (图片字节数据, MIME类型)
        
    Raises:
        ValueError: base64 解码失败时抛出
    """
    try:
        # 处理 data URL 格式: data:image/jpeg;base64,xxxxx
        if base64_str.startswith("data:"):
            # 提取 MIME 类型和 base64 数据
            header, data = base64_str.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            image_data = base64.b64decode(data)
        else:
            # 纯 base64 字符串，尝试推断 MIME 类型
            image_data = base64.b64decode(base64_str)
            # 根据文件头推断 MIME 类型
            if image_data.startswith(b'\xff\xd8\xff'):
                mime_type = "image/jpeg"
            elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
                mime_type = "image/png"
            elif image_data.startswith(b'BM'):
                mime_type = "image/bmp"
            else:
                mime_type = "image/jpeg"  # 默认
        
        return image_data, mime_type
    except Exception as e:
        raise ValueError(f"Base64 解码失败: {str(e)}")


@router.post(
    "/compare_by_base64",
    operation_id="api_compare_images_by_base64",
    summary="对比两张图片中的物品是否相同（通过 Base64 编码）",
    description=f"MCP 工具专用接口，接受 Base64 编码的图片字符串。图片支持类型:{ALLOWED_EXTENSIONS}",
    response_model=SearchResponse,
)
async def api_compare_images_by_base64(
    image1_base64: str = Form(..., description="第一张图片的 Base64 编码字符串（支持 data URL 格式）"),
    image2_base64: str = Form(..., description="第二张图片的 Base64 编码字符串（支持 data URL 格式）"),
    scene_description: str = Form(..., description="场景描述信息"),
    image1_filename: Optional[str] = Form(None, description="第一张图片的文件名（可选）"),
    image2_filename: Optional[str] = Form(None, description="第二张图片的文件名（可选）"),
) -> SearchResponse:
    """
    对比两张图片中的物品是否相同（Base64 编码模式，MCP 工具专用接口）
    
    此接口专门为 MCP 工具调用设计，接受 Base64 编码的图片字符串。
    支持两种格式：
    1. 纯 Base64 字符串: "iVBORw0KGgoAAAANS..."
    2. Data URL 格式: "data:image/jpeg;base64,iVBORw0KGgoAAAANS..."
    
    Args:
        image1_base64: 第一张图片的 Base64 编码字符串
        image2_base64: 第二张图片的 Base64 编码字符串
        scene_description: 场景描述信息，用于指导模型判断
        image1_filename: 第一张图片的文件名（可选，用于日志）
        image2_filename: 第二张图片的文件名（可选，用于日志）
        
    Returns:
        SearchResponse: 包含对比结果的响应
    """
    try:
        logger.info(f"开始处理图片对比请求（Base64）: image1_filename={image1_filename}, image2_filename={image2_filename}, scene={scene_description}")
        
        # 解码 Base64 图片
        try:
            image1_data, image1_type = decode_base64_image(image1_base64)
            image2_data, image2_type = decode_base64_image(image2_base64)
        except ValueError as e:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"Base64 解码失败: {str(e)}",
                data=None
            )
        
        # 验证图片数据有效性
        from backend.utils.process import validate_image
        if not validate_image(image1_data):
            return SearchResponse(
                code=MessageCode.FAIL,
                msg="第一张图片数据无效，无法解析",
                data=None
            )
        
        if not validate_image(image2_data):
            return SearchResponse(
                code=MessageCode.FAIL,
                msg="第二张图片数据无效，无法解析",
                data=None
            )
        
        # 设置文件名（如果没有提供，使用默认值）
        image1_name = image1_filename or f"image1.{image1_type.split('/')[-1]}"
        image2_name = image2_filename or f"image2.{image2_type.split('/')[-1]}"
        
        # 构建DTO
        image_compare_dto = ImageCompareDTO(
            image1_data=image1_data,
            image1_name=image1_name,
            image1_type=image1_type,
            image2_data=image2_data,
            image2_name=image2_name,
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
        
        logger.info(f"图片对比完成（Base64）: is_same={compare_result.is_same}, confidence={compare_result.confidence}")
        
        return SearchResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=result_data,
        )
        
    except ValueError as e:
        err_msg = f"参数错误: {str(e)}"
        logger.error(err_msg)
        return SearchResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=err_msg,
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


@router.post(
    "/compare_by_url",
    operation_id="api_compare_images_by_url",
    summary="对比两张图片中的物品是否相同（通过图片URL）",
    description="接收两张图片的URL地址和一个场景描述，自动下载图片并判断图片中的物品是否是同一个",
    response_model=SearchResponse,
)
async def api_compare_images_by_url(
    image1_url: str = Form(..., description="第一张图片的URL地址"),
    image2_url: str = Form(..., description="第二张图片的URL地址"),
    scene_description: str = Form(..., description="场景描述信息"),
) -> SearchResponse:
    """
    对比两张图片中的物品是否相同（通过图片URL）
    
    此接口接受图片URL地址，自动下载图片后进行对比。
    支持 HTTP/HTTPS 协议的图片URL。
    
    Args:
        image1_url: 第一张图片的URL地址
        image2_url: 第二张图片的URL地址
        scene_description: 场景描述信息，用于指导模型判断
        
    Returns:
        SearchResponse: 包含对比结果的响应
    """
    try:
        # 验证 URL 格式
        from urllib.parse import urlparse
        
        parsed_url1 = urlparse(image1_url)
        parsed_url2 = urlparse(image2_url)
        
        if not parsed_url1.scheme or not parsed_url1.netloc:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第一张图片URL格式无效: {image1_url}",
                data=None
            )
        
        if not parsed_url2.scheme or not parsed_url2.netloc:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第二张图片URL格式无效: {image2_url}",
                data=None
            )
        
        # 验证协议（只支持 HTTP/HTTPS）
        if parsed_url1.scheme not in ["http", "https"]:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第一张图片URL协议不支持，仅支持 http/https: {image1_url}",
                data=None
            )
        
        if parsed_url2.scheme not in ["http", "https"]:
            return SearchResponse(
                code=MessageCode.FAIL,
                msg=f"第二张图片URL协议不支持，仅支持 http/https: {image2_url}",
                data=None
            )
        
        logger.info(f"开始处理图片对比请求（URL）: image1_url={image1_url}, image2_url={image2_url}, scene={scene_description}")
        
        # 构建 URL DTO
        url_compare_dto = ImageCompareByURLDTO(
            image1_url=image1_url,
            image2_url=image2_url,
            scene_description=scene_description,
        )
        
        # 调用service层（异步执行，因为下载图片可能耗时）
        compare_result = await asyncio.to_thread(
            compare_images_by_url_service, url_compare_dto
        )
        
        # 转换为字典格式返回
        result_data = {
            "is_same": compare_result.is_same,
            "confidence": compare_result.confidence,
            "reason": compare_result.reason,
        }
        
        logger.info(f"图片对比完成（URL）: is_same={compare_result.is_same}, confidence={compare_result.confidence}")
        
        return SearchResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=result_data,
        )
        
    except ValueError as e:
        err_msg = f"参数错误: {str(e)}"
        logger.error(err_msg)
        return SearchResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=err_msg,
        )
    except ConnectionError as e:
        err_msg = f"网络连接失败: {str(e)}"
        logger.error(err_msg)
        return SearchResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=err_msg,
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
