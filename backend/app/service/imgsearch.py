# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.app.schema import *
from backend.core.configs import settings
from backend.core.logs.logger import logger
from backend.storage.vdb.milvusdb import MilvusDB
from backend.app.service.vectorize import vectorize_image

def search_image_service(
	image_dto: OneImageSearchDTO,
	milvus_client: MilvusDB = None,
):
	"""
	对图像进行向量化
	
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
		
		resp = milvus_client.search_data(embedding, top_k=5, cosine=0.25)
		

		return resp

	except Exception as e:
		logger.warning(e)
		raise e


if __name__ == "__main__":
	jpgfile = open("C:\\workspace\\python\\web_search\\backend\\app\\service\\GTY-CXF.png", "rb")
	result = search_image(jpgfile.read())
	print(f"result:{result}")

	

