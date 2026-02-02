"""
AI应急智能体服务主入口文件
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import uvicorn
from fastapi_mcp import FastApiMCP
from backend.core.configs import settings
from backend.core.logs.logger import logger
from backend.core.registrar import create_app


# 创建FastAPI应用
app = create_app()
from mcp.types import Tool
from backend.app.schema import *
from fastapi import FastAPI, Request
import json


# 临时加入，抓取智能体的工具调用请求（以后需合并到中间件）
@app.middleware("http")
async def log_mcp_requests(request: Request, call_next):
    if request.url.path == "/mcp":
        # 读取请求体（注意：只能读一次！）
        body = await request.body()
        try:
            payload = json.loads(body.decode())
            logger.info(f"📥 MCP 接收到请求:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"❌ 解析 MCP 请求失败: {e}, 原始 body: {body}")
        
        # 重新构造 request（因为 body 已被消费）
        from starlette.requests import Request as StarletteRequest
        receive = request._receive
        new_request = StarletteRequest(
            scope=request.scope,
            receive=lambda: receive(),  # 重放 body
        )
        response = await call_next(new_request)
    else:
        response = await call_next(request)
    return response

mcp = FastApiMCP(
    app,
    name="以图搜图",
    description="根据输入图像，搜索相似图像",
    include_operations=["upload_image", "search_image"],
    auth_config=None,
    # 将所有可能的响应 schema 放入描述
    describe_all_responses=True,
    # 在描述中包含完整的 JSON schema
    describe_full_response_schema=True,
)


# mcp.server._require_session = False
mcp.mount_http()

if __name__ == "__main__":
    logger.info("启动FastAPI应用")
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, workers=settings.workers) 
    logger.info("FastAPI应用已启动")
