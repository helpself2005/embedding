"""
应用生命周期管理模块
负责处理FastAPI应用的生命周期事件
"""
import asyncio  
from fastapi import FastAPI
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client
from backend.core.logs.logger import logger
from backend.storage.milvus_client import create_milvus_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔄 启动中：建立 MCP 长连接")
    try:
        # # 手动进入 sse_client 上下文
        # sse_ctx = sse_client("http://0.0.0.0:10090/sse")
        # read, write = await sse_ctx.__aenter__()

        # session_ctx = ClientSession(read, write)
        # session = await session_ctx.__aenter__()

        # await session.initialize()
        # tools = await session.list_tools()
        # available_tools = [tool.name for tool in tools.tools]
        # logger.info(f"可用的工具列表: {available_tools}")

        # # 保存到 FastAPI app 的状态
        # app.state.session = session
        # app.state.available_tools = available_tools

        logger.info("[FastAPI] 初始化 Milvus 连接")
        app.state.milvus_client = create_milvus_client()

        yield
    except Exception as e:
        logger.error(f"生命周期管理出错: {e}")
        raise
    finally:
        # logger.info("🧹 清理中：关闭 MCP 连接")
        # await session_ctx.__aexit__(None, None, None)
        # await sse_ctx.__aexit__(None, None, None)
        logger.info("✅ 清理完成")


async def _startup_events(app: FastAPI) -> None:
    """
    应用启动时的初始化事件
    
    Args:
        app: FastAPI应用实例
    """
    pass


async def _shutdown_events(app: FastAPI, extract_task: asyncio.Task) -> None:
    """
    应用关闭时的清理事件
    
    Args:
        app: FastAPI应用实例
    """
    pass

