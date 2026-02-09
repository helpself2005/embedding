from typing import Optional
from pydantic import BaseModel, Field


class ImageCompareDTO(BaseModel):
    """图片对比请求DTO"""
    image1_data: bytes = Field(..., description="第一张图片的字节数据")
    image1_name: str = Field(..., description="第一张图片的文件名")
    image1_type: str = Field(..., description="第一张图片的MIME类型")
    image2_data: bytes = Field(..., description="第二张图片的字节数据")
    image2_name: str = Field(..., description="第二张图片的文件名")
    image2_type: str = Field(..., description="第二张图片的MIME类型")
    scene_description: str = Field(..., description="场景描述信息")


class ImageCompareResult(BaseModel):
    """图片对比结果"""
    is_same: bool = Field(..., description="是否是同一个物品")
    confidence: float = Field(..., description="置信度，0.0-1.0之间的浮点数")
    reason: str = Field(..., description="详细的判断理由")


class ImageCompareByURLDTO(BaseModel):
    """通过URL对比图片的请求DTO"""
    image1_url: str = Field(..., description="第一张图片的URL地址")
    image2_url: str = Field(..., description="第二张图片的URL地址")
    scene_description: str = Field(..., description="场景描述信息")


class ImageCompareByLocalURLDTO(BaseModel):
    """通过本地URL对比图片的请求DTO"""
    image1_local_url: str = Field(..., description="第一张图片的本地URL地址")
    image2_local_url: str = Field(..., description="第二张图片的本地URL地址")
    scene_description: str = Field(..., description="场景描述信息")


class ImageCompareResponse(BaseModel):
    """图片对比响应DTO"""
    code: int = Field(200, description="状态码")
    msg: str = Field("", description="提示信息")
    data: Optional[ImageCompareResult] = Field(None, description="对比结果")
