# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from pymilvus import AnnSearchRequest
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from backend.app.schema import *
from backend.utils.mdhash import (
	compute_mdhash_id,
)
from backend.core.configs import settings
from backend.core.logs.logger import logger
from backend.storage.vdb.milvusdb import MilvusDB
from backend.app.service.vectorize import vectorize_image

def insert_image_service(
	image_dto: OneImageUploadDTO,
	milvus_client: MilvusDB = None,
):
	"""
	对图像进行向量化, 并插入
	
	Args:
		image_dto: 图像文件内容
		milvus_client: milvus client变量
		
	Returns:
		tuple: (embedding, response) - embedding 向量和原始响应对象
		       如果失败则返回 (None, response)
		       embedding 已经是清理后的普通 Python 列表
		
	Raises:
		Exception: 失败时抛出异常
	"""
	try:
		
		vector_response = vectorize_image(image_dto)

		embedding = vector_response.get("output", [])
		
		data_raw = [{
				"class_id": compute_mdhash_id(image_dto.file_class),
				"class_name": image_dto.file_class,
				"file_path": image_dto.file_name,
				"file_content": "",
				"vector": embedding,
			}]

		resp = milvus_client.insert_data(data_raw)

		return resp

	except Exception as e:
		logger.warning(e)
		raise e


if __name__ == "__main__":
	jpgfile = open("C:\\workspace\\python\\web_search\\backend\\app\\service\\GTY-CXF.png", "rb")
	image_dto = OneImageUploadDTO(**{"file_data":jpgfile.read(), "file_name":"test.jpg", "file_type": "image/jpeg",  "file_class": "0"})
	result = insert_image(image_dto)
	print(f"result:{result}")

	

