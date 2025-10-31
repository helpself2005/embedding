import os
import time
from http import HTTPStatus
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 导入服务模块
from milvus_client import create_milvus_collection, get_milvus_client, MILVUS_COLLECTION
from embedding_service import (
	vectorize_image,
	get_error_detail,
	prepare_embedding_for_milvus
)
from utils import clean_for_serialization

app = FastAPI()

# CORS（如需前端跨域）
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        create_milvus_collection()
    except Exception as e:
        # 不抛出致命错误，允许服务启动，但记录初始化失败
        print(f"[Milvus] 初始化失败: {e}")

@app.get("/health")
async def health():
	return {"status": "ok"}

@app.post("/vectorize")
async def vectorize_image_endpoint(file: UploadFile = File(...)):
	"""
	上传图像文件并返回向量化结果
	
	Args:
		file: 上传的图像文件
		
	Returns:
		JSON响应，包含向量化结果
	"""
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="上传文件不是图片类型")
	
	try:
		contents = await file.read()
		
		# 使用 embedding_service 进行向量化
		embedding, resp = vectorize_image(contents, file.content_type)
		
		# 成功：HTTPStatus.OK
		if getattr(resp, "status_code", None) == HTTPStatus.OK:
			# 如果拿不到embedding，直接透传output，方便排查
			if embedding is None:
				output = getattr(resp, "output", None)
				return JSONResponse(content={
					"output": output,
					"success": True
				})
			return JSONResponse(content={
				"embedding": embedding,
				"dim": len(embedding),
				"success": True
			})
		else:
			detail = get_error_detail(resp)
			raise HTTPException(status_code=502, detail=detail)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=502, detail=f"调用DashScope异常: {str(e)}")


@app.post("/image-vector-save")
async def image_vector_save(
	file: UploadFile = File(...),
	doc_id: int = None,
	content: str = None
):
	"""
	上传图像文件，向量化，并将结果保存到 Milvus 向量数据库
	
	Args:
		file: 上传的图像文件
		doc_id: 文档ID（可选，不提供则使用时间戳）
		content: 文本内容（可选，可用于存储图片描述等信息）
	
	Returns:
		JSON响应，包含插入结果和向量信息
	"""
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="上传文件不是图片类型")
	
	try:
		contents = await file.read()
	except Exception:
		raise HTTPException(status_code=400, detail="读取文件失败")

	# 向量化图像
	try:
		embedding, resp = vectorize_image(contents, file.content_type)
		
		if embedding is None:
			detail = get_error_detail(resp)
			raise HTTPException(status_code=502, detail=f"无法从响应中提取向量: {detail}")
		
		# 生成 doc_id（如果未提供）
		if doc_id is None:
			doc_id = int(time.time() * 1000)  # 使用毫秒时间戳
		
		# 准备 content（如果未提供，使用文件名）
		if content is None:
			content = file.filename or f"image_{doc_id}"
		
		# 获取 Milvus 客户端并插入数据
		try:
			client = get_milvus_client()
			
			# 使用 embedding_service 准备向量数据
			embedding_clean = prepare_embedding_for_milvus(embedding)
			
			# 准备插入的数据（使用清理后的数据）
			data_raw = [{
				"doc_id": int(doc_id),
				"vector": embedding_clean,
				"content": str(content[:9000])
			}]
			
			# 使用清理函数彻底清理整个数据对象
			data = clean_for_serialization(data_raw)
			
			# 验证数据可以序列化（用于调试）
			try:
				import json
				json.dumps(data)  # 尝试序列化以验证
			except Exception as json_err:
				raise HTTPException(status_code=500, detail=f"数据序列化验证失败: {str(json_err)}")
			
			# 插入数据到 Milvus
			result = client.insert(
				collection_name=MILVUS_COLLECTION,
				data=data
			)
			
			# 将 insert_result 转换为可序列化的格式
			insert_result_serializable = None
			if result:
				try:
					# 使用清理函数彻底清理 result 对象
					insert_result_serializable = clean_for_serialization(result)
					
					# 如果结果不是字典，尝试提取常见属性
					if not isinstance(insert_result_serializable, dict):
						result_dict = {}
						if hasattr(result, 'insert_count'):
							result_dict["insert_count"] = int(result.insert_count)
						if hasattr(result, 'ids'):
							ids = result.ids
							if ids is not None:
								try:
									result_dict["ids"] = clean_for_serialization(ids)
								except:
									result_dict["ids"] = []
						if result_dict:
							insert_result_serializable = result_dict
						else:
							insert_result_serializable = {
								"status": "success",
								"message": "数据已插入"
							}
				except Exception as e:
					# 如果序列化失败，只返回成功状态
					insert_result_serializable = {
						"status": "success",
						"message": "数据已插入"
					}
			
			return JSONResponse(content={
				"success": True,
				"doc_id": doc_id,
				"vector_dim": len(embedding),
				"content": content,
				"insert_result": insert_result_serializable,
				"message": "向量已成功保存到 Milvus"
			})
		
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"保存到 Milvus 失败: {str(e)}")
	
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=502, detail=f"处理失败: {str(e)}")
@app.post("/image-search")
async def image_search(
	file: UploadFile = File(...),
	top_k: int = 2
):
	"""
	上传图像文件，向量化，并在 Milvus 中检索最相似的图像
	
	Args:
		file: 上传的图像文件
		top_k: 返回最相似的结果数量（默认 5）
	
	Returns:
		JSON响应，包含最相似的图像列表
	"""
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="上传文件不是图片类型")
	
	try:
		contents = await file.read()
	except Exception:
		raise HTTPException(status_code=400, detail="读取文件失败")

	# 向量化图像
	try:
		embedding, resp = vectorize_image(contents, file.content_type)
		
		if embedding is None:
			detail = get_error_detail(resp)
			raise HTTPException(status_code=502, detail=f"无法从响应中提取向量: {detail}")
		
		# 使用 embedding_service 准备向量数据
		embedding_clean = prepare_embedding_for_milvus(embedding)
		
		# 在 Milvus 中搜索
		try:
			client = get_milvus_client()
			
			# 确保 collection 已加载（搜索前必须加载）
			try:
				client.load_collection(collection_name=MILVUS_COLLECTION)
			except Exception as load_err:
				# 如果加载失败，尝试检查 collection 是否存在
				if not client.has_collection(MILVUS_COLLECTION):
					raise HTTPException(status_code=404, detail=f"Collection '{MILVUS_COLLECTION}' 不存在")
				
				# 如果加载失败且是因为没有索引，尝试创建索引
				error_msg = str(load_err).lower()
				if "index not found" in error_msg or "700" in error_msg:
					print(f"[Milvus] Collection '{MILVUS_COLLECTION}' 没有索引，正在创建索引...")
					try:
						# 为已存在的 collection 创建索引（使用官方文档推荐的方式）
						index_params = client.prepare_index_params()
						index_params.add_index(
							field_name="vector",
							index_type="AUTOINDEX",
							metric_type="L2"
						)
						
						client.create_index(
							collection_name=MILVUS_COLLECTION,
							field_name="vector",
							index_params=index_params
						)
						print(f"[Milvus] 为 Collection '{MILVUS_COLLECTION}' 的 vector 字段创建索引成功")
						
						# 索引创建后再次尝试加载
						client.load_collection(collection_name=MILVUS_COLLECTION)
						print(f"[Milvus] Collection '{MILVUS_COLLECTION}' 已加载")
					except Exception as index_err:
						raise HTTPException(status_code=500, detail=f"创建索引失败: {str(index_err)}")
				else:
					raise HTTPException(status_code=500, detail=f"加载 collection 失败: {str(load_err)}")
			
			# 执行向量搜索
			search_results = client.search(
				collection_name=MILVUS_COLLECTION,
				data=[embedding_clean],  # 查询向量列表
				limit=top_k,  # 返回 top_k 个结果
				output_fields=["doc_id", "content"]  # 返回的字段
			)
			
			# 处理搜索结果
			results = []
			if search_results and len(search_results) > 0:
				# search_results 是一个列表，每个元素对应一个查询向量的结果
				query_results = search_results[0]  # 第一个查询向量的结果
				
				if isinstance(query_results, list):
					for hit in query_results:
						result_item = {}
						
						# 处理不同格式的搜索结果
						if isinstance(hit, dict):
							# 如果是字典格式
							result_item = {
								"id": hit.get("id"),
								"doc_id": hit.get("doc_id"),
								"content": hit.get("content"),
								"distance": hit.get("distance"),
								"score": hit.get("distance")  # 距离越小越相似
							}
						else:
							# 如果是对象格式，尝试访问属性
							result_item = {}
							if hasattr(hit, 'id'):
								try:
									result_item["id"] = clean_for_serialization(hit.id)
								except:
									result_item["id"] = None
							
							if hasattr(hit, 'distance'):
								try:
									distance = clean_for_serialization(hit.distance)
									result_item["distance"] = float(distance) if distance is not None else None
									result_item["score"] = result_item["distance"]
								except:
									result_item["distance"] = None
									result_item["score"] = None
							
							# 获取实体数据
							if hasattr(hit, 'entity'):
								entity = hit.entity
								if isinstance(entity, dict):
									result_item["doc_id"] = entity.get("doc_id")
									result_item["content"] = entity.get("content")
								else:
									result_item["doc_id"] = clean_for_serialization(getattr(entity, "doc_id", None))
									result_item["content"] = clean_for_serialization(getattr(entity, "content", None))
							elif hasattr(hit, 'get'):
								# 如果 hit 本身有 get 方法，尝试直接获取
								result_item["doc_id"] = hit.get("doc_id")
								result_item["content"] = hit.get("content")
						
						# 清理结果项，确保所有值都可序列化
						result_item = clean_for_serialization(result_item)
						results.append(result_item)
			
			return JSONResponse(content={
				"success": True,
				"query_vector_dim": len(embedding_clean),
				"top_k": top_k,
				"results_count": len(results),
				"results": results,
				"message": f"找到 {len(results)} 个相似图像"
			})
		
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"Milvus 搜索失败: {str(e)}")
	
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=502, detail=f"处理失败: {str(e)}")


def main():
	# 允许通过环境变量控制host/port
	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "8000"))
	import uvicorn
	uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
	main()
