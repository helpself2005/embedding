def clean_for_serialization(obj):
	"""
	递归清理对象，将所有 RepeatedScalarContainer 等特殊类型转换为普通 Python 类型
	
	Args:
		obj: 需要清理的对象
		
	Returns:
		清理后的对象，确保所有特殊类型都已转换为普通 Python 类型
	"""
	if isinstance(obj, (int, float, str, bool, type(None))):
		return obj
	elif isinstance(obj, (list, tuple)):
		return [clean_for_serialization(item) for item in obj]
	elif isinstance(obj, dict):
		return {k: clean_for_serialization(v) for k, v in obj.items()}
	elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
		# 处理 RepeatedScalarContainer 等特殊容器类型
		try:
			return [clean_for_serialization(item) for item in obj]
		except:
			return [float(x) for x in obj]
	else:
		# 尝试转换为基本类型
		try:
			return float(obj)
		except:
			return str(obj)


def prepare_embedding_for_milvus(embedding):
	"""
	准备向量数据用于 Milvus 插入或搜索
	
	Args:
		embedding: 原始向量数据（可能是各种格式）
		
	Returns:
		list: 清理后的浮点数列表
		
	Raises:
		ValueError: 如果向量格式不正确
	"""
	# 使用清理函数彻底清理 embedding，确保没有 RepeatedScalarContainer
	embedding_clean = clean_for_serialization(embedding)
	
	# 最终验证：确保是列表且所有元素都是 float
	if not isinstance(embedding_clean, list):
		embedding_clean = list(embedding_clean)
	
	embedding_clean = [float(x) for x in embedding_clean]
	
	return embedding_clean

