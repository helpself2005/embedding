import os
import io
import base64
from http import HTTPStatus
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from dotenv import load_dotenv

# DashScope SDK
import dashscope
from dashscope import MultiModalEmbedding

# 加载.env配置
load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY") or "sk-bbc64eaa6c7d4fc4a15df033554d2d5c"
# 使用示例中的模型名，允许通过环境变量覆盖
EMBEDDING_MODEL = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "tongyi-embedding-vision-plus")

# 设置SDK全局key
dashscope.api_key = API_KEY

app = FastAPI()

# CORS（如需前端跨域）
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.get("/health")
async def health():
	return {"status": "ok"}

@app.post("/vectorize")
async def vectorize_image(file: UploadFile = File(...)):
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="上传文件不是图片类型")
	try:
		contents = await file.read()
		# 校验可打开
		img = Image.open(io.BytesIO(contents))
		img.verify()
	except Exception:
		raise HTTPException(status_code=400, detail="图片文件解析失败")

	# 推断mime 并转成 data URL
	mime = file.content_type if file.content_type and file.content_type.startswith("image/") else "image/jpeg"
	b64 = base64.b64encode(contents).decode("utf-8")
	data_url = f"data:{mime};base64,{b64}"

	try:
		# 按示例：input 为列表，元素为 { 'image': data_url }
		resp = MultiModalEmbedding.call(
			model=EMBEDDING_MODEL,
			input=[{"image": data_url}]
		)

		# 成功：HTTPStatus.OK
		if getattr(resp, "status_code", None) == HTTPStatus.OK:
			output = getattr(resp, "output", None)
			# 解析 embedding
			embedding = None
			if isinstance(output, dict):
				if "embeddings" in output and isinstance(output["embeddings"], list) and output["embeddings"]:
					first = output["embeddings"][0]
					if isinstance(first, dict) and "embedding" in first:
						embedding = first["embedding"]
				elif "embedding" in output and isinstance(output["embedding"], list):
					embedding = output["embedding"]
			# 如果拿不到embedding，直接透传output，方便排查
			if embedding is None:
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
			detail = {
				"status_code": getattr(resp, "status_code", None),
				"request_id": getattr(resp, "request_id", ""),
				"code": getattr(resp, "code", ""),
				"message": getattr(resp, "message", ""),
				"output": getattr(resp, "output", None),
				"usage": getattr(resp, "usage", None),
			}
			raise HTTPException(status_code=502, detail=detail)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=502, detail=f"调用DashScope异常: {str(e)}")


def main():
	# 允许通过环境变量控制host/port
	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "8000"))
	import uvicorn
	uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
	main()
