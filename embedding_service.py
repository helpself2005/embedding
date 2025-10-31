import os
import io
import base64
import sys
import json
from http import HTTPStatus
from PIL import Image
from dotenv import load_dotenv
import dashscope
from dashscope import MultiModalEmbedding

# 加载.env配置
load_dotenv()

# DashScope 配置
API_KEY = os.getenv("DASHSCOPE_API_KEY") or "sk-bbc64eaa6c7d4fc4a15df033554d2d5c"
EMBEDDING_MODEL = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "tongyi-embedding-vision-plus")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1152"))

# 设置SDK全局key
dashscope.api_key = API_KEY


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


def extract_embedding_from_response(resp) -> list:
	"""
	从 DashScope 响应中提取 embedding 向量
	
	Args:
		resp: DashScope API 的响应对象
		
	Returns:
		list: 提取并处理后的 embedding 向量列表，如果提取失败返回 None
	"""
	if getattr(resp, "status_code", None) != HTTPStatus.OK:
		return None
	
	output = getattr(resp, "output", None)
	
	# 打印原始输出数据大小
	if output is not None:
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
		
		# 估算向量对象的内存大小
		vector_memory_size = get_object_size(embedding)
		
		print(f"[Embedding] 通义千问返回向量大小: {len(embedding)} 维")
		print(f"[Embedding] 向量数据大小: {vector_size_formatted} ({vector_size_bytes} 字节)")
		print(f"[Embedding] 向量内存占用: {format_size(vector_memory_size)}")
	
	return embedding


def vectorize_image(
	image_contents: bytes,
	content_type: str = None,
	dimensions: int = None
):
	"""
	对图像进行向量化
	
	Args:
		image_contents: 图像文件的字节内容
		content_type: MIME 类型
		dimensions: 向量维度，默认使用配置的维度
		
	Returns:
		tuple: (embedding, response) - embedding 向量和原始响应对象
		       如果失败则返回 (None, response)
		       embedding 已经是清理后的普通 Python 列表
		
	Raises:
		ValueError: 图片文件无效时抛出
		Exception: 调用 DashScope API 失败时抛出异常
	"""
	# 验证图片
	if not validate_image(image_contents):
		raise ValueError("图片文件解析失败")
	
	# 转换为 data URL
	data_url = image_to_data_url(image_contents, content_type)
	
	# 使用配置的维度或传入的维度
	dims = dimensions or EMBEDDING_DIMENSIONS
	
	# 调用 DashScope API
	resp = MultiModalEmbedding.call(
		model=EMBEDDING_MODEL,
		input=[{"image": data_url}],
		dimensions=dims
	)
	
	# 提取并清理 embedding
	embedding = extract_embedding_from_response(resp)
	
	# 打印 API 响应数据流大小
	try:
		# 尝试序列化响应对象来估算大小
		resp_dict = {
			"status_code": getattr(resp, "status_code", None),
			"output": getattr(resp, "output", None),
			"usage": getattr(resp, "usage", None),
		}
		resp_json = json.dumps(resp_dict, ensure_ascii=False)
		resp_size_bytes = len(resp_json.encode('utf-8'))
		resp_size_formatted = format_size(resp_size_bytes)
		print(f"[Embedding] API 响应数据流大小: {resp_size_formatted} ({resp_size_bytes} 字节)")
	except Exception as e:
		print(f"[Embedding] 无法计算响应大小: {e}")
	
	# 打印向量信息
	if embedding is not None:
		print(f"[Embedding] 向量化完成，向量维度: {len(embedding)}")
		print(f"[Embedding] 请求的维度: {dims}，实际返回维度: {len(embedding)}")
		
		# 计算向量 JSON 序列化后的大小
		try:
			embedding_json = json.dumps(embedding)
			embedding_json_size = len(embedding_json.encode('utf-8'))
			print(f"[Embedding] 向量 JSON 序列化大小: {format_size(embedding_json_size)} ({embedding_json_size} 字节)")
		except Exception:
			pass
	else:
		print(f"[Embedding] 警告: 未能提取向量，响应状态码: {getattr(resp, 'status_code', 'unknown')}")
	
	return embedding, resp


def prepare_embedding_for_milvus(embedding):
	"""
	准备向量数据用于 Milvus 插入或搜索
	
	Args:
		embedding: 原始向量数据（从 vectorize_image 返回的已经是清理后的格式）
		
	Returns:
		list: 清理后的浮点数列表，确保完全可序列化
		
	Raises:
		ValueError: 如果向量格式不正确
	"""
	if embedding is None:
		raise ValueError("embedding 不能为 None")
	
	# 再次确保是列表且所有元素都是 float
	if not isinstance(embedding, list):
		embedding = list(embedding)
	
	embedding_clean = [float(x) for x in embedding]
	
	return embedding_clean


def get_error_detail(resp) -> dict:
	"""
	从响应中提取错误详情
	
	Args:
		resp: DashScope API 的响应对象
		
	Returns:
		dict: 包含错误详情的字典
	"""
	return {
		"status_code": getattr(resp, "status_code", None),
		"request_id": getattr(resp, "request_id", ""),
		"code": getattr(resp, "code", ""),
		"message": getattr(resp, "message", ""),
		"output": getattr(resp, "output", None),
		"usage": getattr(resp, "usage", None),
	}

