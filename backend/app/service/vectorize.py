# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
import dashscope
from dashscope import MultiModalEmbedding
from requests.exceptions import (
	SSLError,
	ConnectionError, 
	HTTPError, 
	RequestException
)
from backend.utils.process import (
	validate_image,
	image_to_data_url,
	get_embedding_from_response,
)
from backend.app.schema import *
from backend.core.configs import settings
from backend.core.logs.logger import logger


def vectorize_image(
	image_dto: OneImageUploadDTO,
):
	"""
	对图像进行向量化
	
	Args:
		image_dto: 图像文件内容
		
	Returns:
		tuple: (embedding, response) - embedding 向量和原始响应对象
		       如果失败则返回 (None, response)
		       embedding 已经是清理后的普通 Python 列表
		
	Raises:
		ValueError: 图片文件无效时抛出
		SSLError, ConnectionError, HTTPError, RequestException: 调用 DashScope API 失败时抛出异常
		Exception: 其他失败时抛出异常
	"""
	try:
		# 验证图片
		if not validate_image(image_dto.file_data):
			raise ValueError("图片文件解析失败")
		
		# 转换为 data URL
		data_url = image_to_data_url(image_dto.file_data, image_dto.file_type)
		
		if settings.embedding_provider == "dashscope":
			# 调用 DashScope API
			resp = MultiModalEmbedding.call(
				model=settings.dashscope_embedding_model,
				input=[{"image": data_url}],
				api_key=settings.dashscope_embedding_api_key,
				dimensions=settings.dashscope_embedding_dims,
			)
		
		# 提取并清理 embedding
		embedding = get_embedding_from_response(resp)
		if not embedding:
			ValueError("图像向量为None")
		# 返回结果
		resp_dict = {
			"status_code": getattr(resp, "status_code", None),
			"request_id": getattr(resp, "request_id", ""),
			"code": getattr(resp, "code", ""),
			"message": getattr(resp, "message", ""),
			"output": embedding,
			"usage": getattr(resp, "usage", None),
		}
		
		return resp_dict

	except ValueError as e:
		raise e
	except (SSLError, ConnectionError, HTTPError, RequestException) as e:
		logger.warning(f"调用向量化模型事报错: {resp_dict}")
		raise e
	except Exception as e:
		raise e


if __name__ == "__main__":
	jpgfile = open("C:\\workspace\\python\\web_search\\backend\\app\\service\\GTY-CXF.png", "rb")
	result = vectorize_image(jpgfile.read())
	print(f"result:{result}")

	

