# -*- coding: utf-8 -*-
"""
本地文件路径图片对比接口模块
"""
import asyncio
import traceback
from fastapi import APIRouter
from backend.app.schema import ApiResponse
from backend.app.schema.imgcompare import ImageCompareByLocalURLDTO, ImageCompareResult
from backend.core.errors import MessageCode, MessageStatus
from backend.app.service.imgcompare import compare_images_by_local_url_service
from backend.core.logs.logger import logger

router = APIRouter()


@router.post(
    "/compare_by_local_url",
    operation_id="api_compare_images_by_local_url",
    summary="对比两张图片中的物品是否相同（通过本地文件路径）",
    description="接收两张图片的本地文件路径和一个场景描述，读取本地图片文件并判断图片中的物品是否是同一个",
    response_model=ApiResponse,
)
async def api_compare_images_by_local_url(
    local_url_compare_dto: ImageCompareByLocalURLDTO,
) -> ApiResponse:
    """
    对比两张图片中的物品是否相同（通过本地文件路径）
    
    此接口接受本地文件路径，读取文件后进行对比。
    支持的文件格式：.jpg, .jpeg, .png, .bmp
    
    Args:
        local_url_compare_dto: 包含两张图片本地路径和场景描述的DTO对象
        
    Returns:
        ApiResponse: 包含对比结果的响应
    """
    try:
        logger.info(
            f"开始处理图片对比请求（本地文件路径）: "
            f"image1_local_url={local_url_compare_dto.image1_local_url}, "
            f"image2_local_url={local_url_compare_dto.image2_local_url}, "
            f"scene={local_url_compare_dto.scene_description}"
        )
        
        # 调用service层（异步执行，因为读取文件可能耗时）
        compare_result = await asyncio.to_thread(
            compare_images_by_local_url_service, local_url_compare_dto
        )
        
        # 转换为字典格式返回
        result_data = {
            "is_same": compare_result.is_same,
            "confidence": compare_result.confidence,
            "reason": compare_result.reason,
        }
        
        logger.info(
            f"图片对比完成（本地文件路径）: "
            f"is_same={compare_result.is_same}, "
            f"confidence={compare_result.confidence}"
        )
        
        return ApiResponse(
            code=MessageCode.SUCCESS,
            msg=MessageStatus.SUCCESS,
            data=result_data,
        )
        
    except FileNotFoundError as e:
        err_msg = f"文件不存在: {str(e)}"
        logger.error(err_msg)
        return ApiResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=err_msg,
        )
    except ValueError as e:
        err_msg = f"参数验证失败: {str(e)}"
        logger.error(err_msg)
        return ApiResponse(
            code=MessageCode.FAIL,
            msg=MessageStatus.FAIL,
            data=err_msg,
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
