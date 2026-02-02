# -*- coding: utf-8 -*-
import os
import sys
import json
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import dashscope
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
from backend.app.schema.imgcompare import ImageCompareDTO, ImageCompareResult
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
        
        # 将图片转换为 data URL
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
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "image": image1_data_url,
                        "type": "image"
                    },
                    {
                        "image": image2_data_url,
                        "type": "image"
                    },
                    {
                        "text": prompt,
                        "type": "text"
                    }
                ]
            }
        ]
        
        # 调用 DashScope Generation API
        logger.info(f"调用 qwen3-vl-flash 模型进行图片对比，场景描述: {image_compare_dto.scene_description}")
        
        # 设置 API Key
        dashscope.api_key = settings.dashscope_embedding_api_key
        
        resp = dashscope.Generation.call(
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
            # 尝试多种可能的响应格式
            choices = output.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "") or message.get("text", "")
            else:
                content = output.get("text", "") or output.get("content", "")
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
