import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    # 连接到 MCP Server 的 HTTP(S) 地址
    async with streamable_http_client("http://localhost:8000/mcp") as (read, write, _):
        # 创建 session
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()

            # 列出工具
            result = await session.list_tools()
            # print("Available tools:", [tool.name for tool in result.tools])
            print("Available tools:")
            for tool in result.tools:
                print(f"- {tool.name}")
                print(f"  desc   : {tool.description}")
                print(f"  schema : {tool.inputSchema}")
            

asyncio.run(main())
