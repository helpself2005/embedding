# agent_cli.py
import asyncio
from pathlib import Path
from typing import List

import aiofiles
from fastapi import UploadFile
from agno.agent import Agent
from agno.tools.mcp import MCPTools
from agno.models.openai import OpenAIChat
from agno.models.base import Message

import base64
def image_to_base64(file_path):
    """
    将给定路径的图像文件编码为 base64 字符串。

    :param file_path: 图像文件的路径。
    :return: 返回图像文件的 base64 编码字符串。
    """
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string

async def main():
    # === 1. 配置模型 ===
    model = OpenAIChat(
        id="",
        api_key="",
        base_url="",
    )

    # 上一次 assistant 消息（如果没有就传空）
    mcp_tools = MCPTools(transport="streamable-http", url="http://127.0.0.1:8033/mcp")
    await mcp_tools.connect()
    # === 2. 创建智能体 ===
    agent = Agent(
        name="Image Search Agent",
        model=model,
        tools=[mcp_tools],
        markdown=False,
    )

    # === 3. 准备文件 ===
    image_path = "C:/workspace/python/web_search/backend/JT-AEC2361G 正.png"

    # 异步构建 UploadFile
    # file_data = image_to_base64(image_path)


    user_prompt = f"请搜索与这张图片相似的内容,  {image_path}"

    # === 4. 执行搜索 ===
    print("🤖 智能体开始搜索相似图像...")
    try:
        response = await agent.arun(
            user_prompt,
            # files=files # 对应后端 search_image 的 files 参数
        )
        print("\n💬 最终回答:")
        print(response)
    except Exception as e:
        print(f"💥 执行失败: {e}")
    finally:
        await mcp_tools.close()
        pass


if __name__ == "__main__":
    asyncio.run(main())
