# agent_cli.py
import asyncio
from pathlib import Path
from typing import List
import os
import sys

# 添加项目路径以便导入配置
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiofiles
from fastapi import UploadFile
from agno.agent import Agent
from agno.tools.mcp import MCPTools
from agno.models.openai import OpenAIChat
from agno.models.base import Message
from backend.core.configs import settings
import httpx

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

async def check_mcp_server(url: str, timeout: float = 5.0) -> bool:
    """
    检查 MCP 服务器是否可用
    
    Args:
        url: MCP 服务器 URL
        timeout: 超时时间（秒）
        
    Returns:
        bool: 服务器是否可用
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 尝试访问 FastAPI 的 docs 端点来检查服务器是否运行
            base_url = url.replace("/mcp", "")
            check_urls = [
                f"{base_url}/docs",  # FastAPI 文档页面
                f"{base_url}/",      # 根路径
            ]
            
            for check_url in check_urls:
                try:
                    response = await client.get(check_url)
                    if response.status_code < 500:
                        return True
                except Exception:
                    continue
            
            return False
    except Exception:
        return False


async def main():
    # === 1. 准备两张图片的 URL ===
    # 请根据实际情况修改图片 URL
    image1_url = "https://example.com/image1.jpg"  # 第一张图片的 URL
    image2_url = "https://example.com/image2.jpg"  # 第二张图片的 URL
    
    # 验证 URL 格式（支持 HTTP/HTTPS URL 和 data URL）
    from urllib.parse import urlparse
    
    is_data_url1 = image1_url.startswith("data:image/")
    is_data_url2 = image2_url.startswith("data:image/")
    
    if not is_data_url1:
        parsed_url1 = urlparse(image1_url)
        if not parsed_url1.scheme or not parsed_url1.netloc:
            print(f"⚠️  警告: 图片1 URL 格式无效: {image1_url}")
            print("请修改 image1_url 为有效的图片 URL（http:// 或 https://）或 data URL 格式")
            image1_url = None
        elif parsed_url1.scheme not in ["http", "https"]:
            print(f"⚠️  警告: 图片1 URL 协议不支持: {parsed_url1.scheme}")
            print("仅支持 http:// 或 https:// 协议，或 data URL 格式")
            image1_url = None
    
    if not is_data_url2:
        parsed_url2 = urlparse(image2_url)
        if not parsed_url2.scheme or not parsed_url2.netloc:
            print(f"⚠️  警告: 图片2 URL 格式无效: {image2_url}")
            print("请修改 image2_url 为有效的图片 URL（http:// 或 https://）或 data URL 格式")
            image2_url = None
        elif parsed_url2.scheme not in ["http", "https"]:
            print(f"⚠️  警告: 图片2 URL 协议不支持: {parsed_url2.scheme}")
            print("仅支持 http:// 或 https:// 协议，或 data URL 格式")
            image2_url = None
    
    if not image1_url or not image2_url:
        print("\n❌ 请先设置正确的图片 URL 后再运行")
        print("\n支持的格式:")
        print("  1. HTTP/HTTPS URL: 'https://example.com/image1.jpg'")
        print("  2. Data URL: 'data:image/jpeg;base64,xxx'")
        return

    # === 2. 检查 MCP 服务器是否可用 ===
    mcp_url = "http://127.0.0.1:8080/mcp"
    print(f"\n🔍 检查 MCP 服务器连接...")
    print(f"   URL: {mcp_url}")
    
    server_available = await check_mcp_server(mcp_url)
    if not server_available:
        print(f"❌ 错误: MCP 服务器不可用")
        print(f"   请确保 FastAPI 服务器正在运行:")
        print(f"   - 检查服务器是否在 http://127.0.0.1:8080 上运行")
        print(f"   - 运行命令: python -m backend.main 或 uvicorn backend.main:app --host 0.0.0.0 --port 8080")
        return
    
    print(f"✅ MCP 服务器连接正常")

    # === 3. 配置千问模型 ===
    # 使用 DashScope 的 OpenAI 兼容 API
    # API 文档: https://help.aliyun.com/zh/model-studio/qwen-api-via-dashscope
    model = OpenAIChat(
        id="qwen-plus",  # 模型名称，可选: qwen-plus, qwen-max, qwen-turbo, qwen-flash 等
        api_key=settings.dashscope_embedding_api_key,  # 使用配置文件中的 API Key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # DashScope OpenAI 兼容端点
    )
    
    print(f"\n🤖 使用模型: qwen-plus")
    print(f"🔑 API Key: {settings.dashscope_embedding_api_key[:10]}...")
    print(f"🌐 Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1")

    # === 4. 连接 MCP 工具 ===
    mcp_tools = None
    try:
        print(f"\n🔌 正在连接 MCP 工具...")
        mcp_tools = MCPTools(transport="streamable-http", url=mcp_url)
        await mcp_tools.connect()
        print(f"✅ MCP 工具连接成功")
    except Exception as e:
        print(f"❌ MCP 工具连接失败: {e}")
        print(f"   请检查:")
        print(f"   1. FastAPI 服务器是否正在运行")
        print(f"   2. MCP 端点是否正确配置")
        print(f"   3. 网络连接是否正常")
        return
    
    # === 5. 创建智能体 ===
    agent = Agent(
        name="Image Compare Agent",
        model=model,
        tools=[mcp_tools],
        markdown=False,
    )

    # === 6. 准备场景描述 ===
    scene_description = "两张图片中的报警器是同一个吗"  # 场景描述
    
    # === 7. 使用 Agent 调用 MCP 服务（URL 模式） ===
    print("\n🤖 智能体开始对比图像（通过 MCP 服务，URL 模式）...")
    print(f"📷 图片1 URL: {image1_url}")
    print(f"📷 图片2 URL: {image2_url}")
    print(f"📝 场景描述: {scene_description}")
    print("-" * 50)
    
    # 构建提示词，明确告诉 agent 如何使用 MCP 工具（URL 模式）
    url_type1 = "Data URL" if image1_url.startswith("data:image/") else "HTTP/HTTPS URL"
    url_type2 = "Data URL" if image2_url.startswith("data:image/") else "HTTP/HTTPS URL"
    
    user_prompt = f"""我需要使用 api_compare_images_by_url 工具来对比两张图片中的物品是否相同。

工具参数说明：
- image1_url: 第一张图片的 URL 地址（必需，支持 HTTP/HTTPS URL 或 data URL 格式）
- image2_url: 第二张图片的 URL 地址（必需，支持 HTTP/HTTPS URL 或 data URL 格式）
- scene_description: 场景描述文本（必需）

具体参数值：
- image1_url: "{image1_url[:100]}{'...' if len(image1_url) > 100 else ''}" ({url_type1})
- image2_url: "{image2_url[:100]}{'...' if len(image2_url) > 100 else ''}" ({url_type2})
- scene_description: "{scene_description}"

完整参数：
image1_url = "{image1_url}"
image2_url = "{image2_url}"
scene_description = "{scene_description}"

请调用 api_compare_images_by_url 工具，传入上述三个参数。工具会自动从 URL 下载图片（如果是 HTTP/HTTPS URL）或直接解析（如果是 data URL）并进行对比。"""
    
    try:
        # 使用 agent 调用 MCP 工具
        response = await agent.arun(
            user_prompt,
        )
        
        print("\n💬 Agent 响应:")
        print("-" * 50)
        
        # 提取响应内容
        if hasattr(response, 'content'):
            content = response.content
            print(content)
        else:
            print(response)
        
        # 检查是否有工具执行结果
        if hasattr(response, 'tools') and response.tools:
            print("\n🔧 工具执行结果:")
            for tool_exec in response.tools:
                print(f"   工具: {tool_exec.tool_name}")
                print(f"   参数: {tool_exec.tool_args}")
                print(f"   结果: {tool_exec.result}")
                if tool_exec.tool_call_error:
                    print(f"   ⚠️  工具调用出错")
        
        # 尝试从响应中提取对比结果
        response_str = str(response)
        
        # 尝试解析 JSON 格式的结果
        import json
        import re
        
        # 查找 JSON 格式的结果
        json_match = re.search(r'\{[^{}]*"is_same"[^{}]*\}', response_str, re.DOTALL)
        if json_match:
            try:
                result_json = json.loads(json_match.group(0))
                print("\n" + "=" * 50)
                print("📋 对比结果:")
                print(f"   是否相同: {'✅ 是' if result_json.get('is_same') else '❌ 否'}")
                print(f"   置信度: {result_json.get('confidence', 0):.2%}")
                print(f"   理由: {result_json.get('reason', '')}")
                print("=" * 50)
            except:
                pass
        
        # 检查是否包含对比相关的关键词
        if "is_same" in response_str.lower() or "对比结果" in response_str or "是否相同" in response_str:
            print("\n" + "=" * 50)
            print("📋 检测到对比结果（原始格式）:")
            print(response_str)
            print("=" * 50)
            
    except Exception as e:
        print(f"💥 Agent 执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if mcp_tools:
            try:
                await mcp_tools.close()
                print("\n✅ MCP 连接已关闭")
            except Exception as e:
                print(f"\n⚠️  关闭 MCP 连接时出错: {e}")


if __name__ == "__main__":
    asyncio.run(main())
