import os
import io
import sys
import json
import base64
from PIL import Image
from http import HTTPStatus
from fastapi import Request

def format_size(size_bytes: int) -> str:
	"""
	格式化字节大小为人类可读的格式
	
	Args:
		size_bytes: 字节数
		
	Returns:
		str: 格式化后的大小字符串
	"""
	if size_bytes < 1024:
		return f"{size_bytes} B"
	elif size_bytes < 1024 * 1024:
		return f"{size_bytes / 1024:.2f} KB"
	else:
		return f"{size_bytes / (1024 * 1024):.2f} MB"


def get_object_size(obj) -> int:
	"""
	估算对象的内存大小（字节）
	
	Args:
		obj: 需要计算大小的对象
		
	Returns:
		int: 估算的字节大小
	"""
	try:
		# 尝试使用 sys.getsizeof
		size = sys.getsizeof(obj)
		
		# 如果是列表，递归计算所有元素的大小
		if isinstance(obj, list):
			size += sum(get_object_size(item) for item in obj)
		elif isinstance(obj, dict):
			size += sum(get_object_size(k) + get_object_size(v) for k, v in obj.items())
		
		return size
	except Exception:
		# 如果计算失败，返回 0
		return 0


def validate_image(contents: bytes) -> bool:
	"""
	验证图片文件是否有效
	
	Args:
		contents: 图片文件的字节内容
		
	Returns:
		bool: 如果图片有效返回 True，否则返回 False
	"""
	try:
		img = Image.open(io.BytesIO(contents))
		img.verify()
		return True
	except Exception:
		return False


def image_to_data_url(contents: bytes, content_type: str = None) -> str:
	"""
	将图片内容转换为 data URL 格式
	
	Args:
		contents: 图片文件的字节内容
		content_type: MIME 类型，如果不提供则默认使用 image/jpeg
		
	Returns:
		str: data URL 格式的字符串
	"""
	mime = content_type if content_type and content_type.startswith("image/") else "image/jpeg"
	b64 = base64.b64encode(contents).decode("utf-8")
	return f"data:{mime};base64,{b64}"


def get_embedding_from_response(resp) -> list:
	"""
	从 DashScope 响应中提取 embedding 向量
	
	Args:
		resp: DashScope API 的响应对象
		
	Returns:
		list: 提取并处理后的 embedding 向量列表，如果提取失败返回 None
	"""
	if getattr(resp, "status_code", None) != HTTPStatus.OK:
		return None
	
	if not (output := getattr(resp, "output", None)):
		return None
	
	# 打印原始输出数据大小
	try:
		output_json = json.dumps(output, ensure_ascii=False)
		output_size_bytes = len(output_json.encode('utf-8'))
		output_size_formatted = format_size(output_size_bytes)
		print(f"[Embedding] 原始输出数据大小: {output_size_formatted} ({output_size_bytes} 字节)")
	except Exception:
		pass
	

	embedding = None
	if isinstance(output, dict):
		if "embeddings" in output and isinstance(output["embeddings"], list) and output["embeddings"]:
			first = output["embeddings"][0]
			if isinstance(first, dict) and "embedding" in first:
				embedding = first["embedding"]
		elif "embedding" in output and isinstance(output["embedding"], list):
			embedding = output["embedding"]
	
	if embedding is None:
		return None
	
	# 确保 embedding 是普通的 Python 列表（处理 RepeatedScalarContainer 等特殊类型）
	try:
		if isinstance(embedding, (list, tuple)):
			embedding = [float(x) for x in embedding]
		elif hasattr(embedding, '__iter__') and not isinstance(embedding, (str, bytes)):
			try:
				embedding = list(embedding)
				embedding = [float(x) for x in embedding]
			except:
				embedding = [float(x) for x in iter(embedding)]
		else:
			return None
	except Exception:
		return None
	
	# 打印向量大小和数据流大小
	if embedding is not None:
		# 计算向量数据的字节大小
		vector_size_bytes = len(embedding) * 8  # float64 是 8 字节
		vector_size_formatted = format_size(vector_size_bytes)
		print(f"[Embedding] 通义千问返回向量大小: {len(embedding)} 维")
		print(f"[Embedding] 向量数据大小: {vector_size_formatted} ({vector_size_bytes} 字节)")
	
	return embedding


