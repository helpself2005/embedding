import nest_asyncio
nest_asyncio.apply()  # 允许嵌套事件循环

import asyncio
from agno.tools.mcp import MCPTools

async def main():
    mcp_tools = MCPTools(
        transport="streamable-http",
        url="http://localhost:8000/mcp"
    )
    await mcp_tools.connect()

    print("Discovered tools:", mcp_tools)

    await mcp_tools.close()

# VS Code/Jupyter 不要用 asyncio.run()
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
