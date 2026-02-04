# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import base64
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import dashscope
from dashscope import MultiModalConversation
import httpx
from requests.exceptions import (
    SSLError,
    ConnectionError,
    HTTPError,
    RequestException
)
from backend.utils.process import (
    validate_image,
    image_to_data_url,
)
from backend.app.schema.imgcompare import ImageCompareDTO, ImageCompareResult, ImageCompareByURLDTO
from backend.core.configs import settings
from backend.core.logs.logger import logger


def compare_images_service(image_compare_dto: ImageCompareDTO) -> ImageCompareResult:
    """
    对比两张图片中的物品是否相同
    
    Args:
        image_compare_dto: 包含两张图片和场景描述的DTO
        
    Returns:
        ImageCompareResult: 对比结果，包含是否相同、置信度和理由
        
    Raises:
        ValueError: 图片文件无效时抛出
        SSLError, ConnectionError, HTTPError, RequestException: 调用 DashScope API 失败时抛出异常
        Exception: 其他失败时抛出异常
    """
    try:
        # 验证两张图片
        if not validate_image(image_compare_dto.image1_data):
            raise ValueError("第一张图片文件解析失败")
        if not validate_image(image_compare_dto.image2_data):
            raise ValueError("第二张图片文件解析失败")
        
        # 将图片转换为 data URL 格式（dashscope MultiModalConversation 需要 data URL 格式）
        image1_data_url = image_to_data_url(
            image_compare_dto.image1_data, 
            image_compare_dto.image1_type
        )
        image2_data_url = image_to_data_url(
            image_compare_dto.image2_data, 
            image_compare_dto.image2_type
        )
        
        # 构建 prompt
        prompt = f"""你是一个专业的图像对比分析专家。请分析以下两张图片，根据场景描述判断它们中的物品是否是同一个。

场景描述：{image_compare_dto.scene_description}

请仔细对比两张图片中的物品特征，包括但不限于：
- 外观特征（颜色、形状、大小、纹理等）
- 位置和角度
- 场景上下文

请以JSON格式返回结果，格式如下：
{{
    "is_same": true/false,
    "confidence": 0.0-1.0之间的浮点数,
    "reason": "详细的判断理由"
}}

只返回JSON，不要包含其他文字说明。"""

        # 构建多模态消息
        # dashscope MultiModalConversation 的消息格式：content 是包含 image 和 text 的列表
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "image": image1_data_url
                    },
                    {
                        "image": image2_data_url
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ]
        
        # 调用 DashScope MultiModalConversation API（用于视觉语言模型）
        logger.info(f"调用 qwen3-vl-flash 模型进行图片对比，场景描述: {image_compare_dto.scene_description}")
        
        # 设置 API Key
        dashscope.api_key = settings.dashscope_embedding_api_key
        
        resp = MultiModalConversation.call(
            model=settings.dashscope_vl_model,
            messages=messages,
        )
        
        # 检查响应状态
        if resp.status_code != 200:
            error_msg = f"API调用失败，状态码: {resp.status_code}, 消息: {getattr(resp, 'message', '')}, code: {getattr(resp, 'code', '')}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 提取响应内容
        output = resp.output
        if not output:
            raise ValueError("模型返回结果为空")
        
        # 获取文本内容
        # MultiModalConversation 返回格式：output.choices[0].message.content 可能是数组或字符串
        content = ""
        if isinstance(output, dict):
            choices = output.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                message_content = message.get("content", "")
                
                # content 可能是数组格式（包含 text 和 image）或字符串
                if isinstance(message_content, list):
                    # 如果是数组，提取所有 text 字段
                    text_parts = []
                    for item in message_content:
                        if isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    content = " ".join(text_parts)
                elif isinstance(message_content, str):
                    content = message_content
                else:
                    content = str(message_content)
            else:
                # 如果没有 choices，尝试其他字段
                content = output.get("text", "") or str(output)
        elif isinstance(output, str):
            content = output
        else:
            content = str(output)
        
        if not content:
            raise ValueError("模型返回内容为空")
        
        logger.info(f"模型返回内容: {content}")
        
        # 解析JSON结果
        # 尝试提取JSON部分（可能包含markdown代码块）
        json_match = re.search(r'\{[^{}]*"is_same"[^{}]*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            # 如果没有找到JSON，尝试直接解析整个内容
            json_str = content.strip()
            # 移除可能的markdown代码块标记
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'^```\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
        
        try:
            result_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，尝试从文本中提取信息: {e}")
            # 如果JSON解析失败，尝试从文本中提取信息
            is_same = "true" in content.lower() or "相同" in content or "同一个" in content
            confidence = 0.5  # 默认置信度
            reason = content
            result_dict = {
                "is_same": is_same,
                "confidence": confidence,
                "reason": reason
            }
        
        # 验证和规范化结果
        is_same = bool(result_dict.get("is_same", False))
        confidence = float(result_dict.get("confidence", 0.5))
        # 确保置信度在0-1之间
        confidence = max(0.0, min(1.0, confidence))
        reason = str(result_dict.get("reason", "未提供理由"))
        
        result = ImageCompareResult(
            is_same=is_same,
            confidence=confidence,
            reason=reason
        )
        
        logger.info(f"图片对比完成，结果: is_same={is_same}, confidence={confidence}")
        
        return result
        
    except ValueError as e:
        logger.error(f"参数验证失败: {e}")
        raise e
    except (SSLError, ConnectionError, HTTPError, RequestException) as e:
        logger.error(f"调用DashScope API失败: {e}")
        raise e
    except Exception as e:
        logger.error(f"图片对比服务异常: {e}")
        raise e


def download_image_from_url(url: str, timeout: int = 30) -> tuple[bytes, str]:
    """
    从 URL 下载图片或解析 data URL 格式的图片
    
    支持两种格式：
    1. HTTP/HTTPS URL: 从网络下载图片
    2. Data URL: data:image/jpeg;base64,xxx 格式，直接解析 base64 数据
    
    Args:
        url: 图片的 URL 地址或 data URL 格式字符串
        timeout: 请求超时时间（秒，仅对 HTTP URL 有效）
        
    Returns:
        tuple: (图片字节数据, MIME类型)
        
    Raises:
        ValueError: URL 无效或下载失败时抛出
        ConnectionError: 网络连接失败时抛出
    """
    try:
        # 检查是否是 data URL 格式
        if url.startswith("data:image/"):
            logger.info(f"检测到 data URL 格式，直接解析: {url[:50]}...")
            
            # 解析 data URL: data:image/jpeg;base64,xxxxx
            try:
                header, data = url.split(",", 1)
                mime_type = header.split(":")[1].split(";")[0]
                
                # 解码 base64
                image_data = base64.b64decode(data)
                
                logger.info(f"Data URL 解析成功: MIME类型={mime_type}, 大小={len(image_data)} 字节")
                
                return image_data, mime_type
                
            except Exception as e:
                error_msg = f"Data URL 解析失败: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # 普通 HTTP/HTTPS URL，从网络下载
        logger.info(f"开始从 URL 下载图片: {url}")
        
        # 使用 httpx 下载图片
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            
            # 获取内容类型
            content_type = response.headers.get("content-type", "")
            if content_type and content_type.startswith("image/"):
                mime_type = content_type
            else:
                # 尝试从 URL 推断 MIME 类型
                parsed_url = urlparse(url)
                path = parsed_url.path
                mime_type, _ = mimetypes.guess_type(path)
                if not mime_type or not mime_type.startswith("image/"):
                    # 根据文件扩展名推断
                    ext = os.path.splitext(path)[1].lower()
                    if ext in [".jpg", ".jpeg"]:
                        mime_type = "image/jpeg"
                    elif ext == ".png":
                        mime_type = "image/png"
                    elif ext == ".bmp":
                        mime_type = "image/bmp"
                    else:
                        mime_type = "image/jpeg"  # 默认
            
            image_data = response.content
            
            logger.info(f"图片下载成功: URL={url}, 大小={len(image_data)} 字节, MIME类型={mime_type}")
            
            return image_data, mime_type
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP 错误，状态码: {e.response.status_code}, URL: {url}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except httpx.RequestError as e:
        error_msg = f"请求失败: {str(e)}, URL: {url}"
        logger.error(error_msg)
        raise ConnectionError(error_msg)
    except ValueError as e:
        # 重新抛出 ValueError（可能是 data URL 解析错误）
        raise e
    except Exception as e:
        error_msg = f"处理图片 URL 失败: {str(e)}, URL: {url}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def compare_images_by_url_service(url_compare_dto: ImageCompareByURLDTO) -> ImageCompareResult:
    """
    通过 URL 对比两张图片中的物品是否相同
    
    直接使用 ImageCompareByURLDTO 的字段（image1_url, image2_url, scene_description）
    组织调用大模型，无需下载图片或构建中间对象。
    
    Args:
        url_compare_dto: 包含两张图片 URL 和场景描述的 DTO
        
    Returns:
        ImageCompareResult: 对比结果，包含是否相同、置信度和理由
        
    Raises:
        ValueError: URL 无效时抛出
        Exception: 调用大模型失败时抛出异常
    """
    try:
        logger.info(f"通过 URL 直接调用大模型对比图片: image1_url={url_compare_dto.image1_url}, image2_url={url_compare_dto.image2_url}, scene_description={url_compare_dto.scene_description}")
        
        # 构建 prompt
        prompt = f"""你是一个专业的图像对比分析专家。请分析以下两张图片，根据场景描述判断它们中的物品是否是同一个。

场景描述：{url_compare_dto.scene_description}

请仔细对比两张图片中的物品特征，包括但不限于：
- 外观特征（颜色、形状、大小、纹理等）
- 位置和角度
- 场景上下文

请以JSON格式返回结果，格式如下：
{{
    "is_same": true/false,
    "confidence": 0.0-1.0之间的浮点数,
    "reason": "详细的判断理由"
}}

只返回JSON，不要包含其他文字说明。"""

        # 构建多模态消息，直接使用 DTO 字段
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": url_compare_dto.image1_url},
                    {"image": url_compare_dto.image2_url},
                    {"text": prompt}
                ]
            }
        ]
        
        # 调用 DashScope MultiModalConversation API
        logger.info(f"调用 {settings.dashscope_vl_model} 模型进行图片对比")
        dashscope.api_key = settings.dashscope_embedding_api_key
        
        resp = MultiModalConversation.call(
            model=settings.dashscope_vl_model,
            messages=messages,
        )
        
        # 检查响应状态
        if resp.status_code != 200:
            error_msg = f"API调用失败，状态码: {resp.status_code}, 消息: {getattr(resp, 'message', '')}, code: {getattr(resp, 'code', '')}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 提取响应内容
        output = resp.output
        if not output:
            raise ValueError("模型返回结果为空")
        
        # 获取文本内容
        content = ""
        if isinstance(output, dict):
            choices = output.get("choices", [])
            if choices:
                message_content = choices[0].get("message", {}).get("content", "")
                if isinstance(message_content, list):
                    content = " ".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in message_content if isinstance(item, (dict, str)))
                elif isinstance(message_content, str):
                    content = message_content
                else:
                    content = str(message_content)
            else:
                content = output.get("text", "") or str(output)
        else:
            content = str(output)
        
        if not content:
            raise ValueError("模型返回内容为空")
        
        logger.info(f"模型返回内容: {content}")
        
        # 解析JSON结果
        json_match = re.search(r'\{[^{}]*"is_same"[^{}]*\}', content, re.DOTALL)
        json_str = json_match.group(0) if json_match else re.sub(r'^```json\s*|^```\s*|\s*```$', '', content.strip())
        
        try:
            result_dict = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("JSON解析失败，尝试从文本中提取信息")
            result_dict = {
                "is_same": "true" in content.lower() or "相同" in content or "同一个" in content,
                "confidence": 0.5,
                "reason": content
            }
        
        # 构建结果
        result = ImageCompareResult(
            is_same=bool(result_dict.get("is_same", False)),
            confidence=max(0.0, min(1.0, float(result_dict.get("confidence", 0.5)))),
            reason=str(result_dict.get("reason", "未提供理由"))
        )
        
        logger.info(f"通过 URL 图片对比完成，结果: is_same={result.is_same}, confidence={result.confidence}")
        return result
        
    except ValueError as e:
        logger.error(f"参数验证失败: {e}")
        raise e
    except Exception as e:
        logger.error(f"通过 URL 图片对比服务异常: {e}")
        raise e
