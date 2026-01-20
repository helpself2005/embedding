from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel,Field
import uvicorn

app = FastAPI()

class HelloRequest(BaseModel):
    name: str= Field(..., description="城市名称，例如 '北京'")

class Helloresponse(BaseModel):
    code:str
    message: str


@app.post(
    "/hello",
    operation_id="say_hello",
    summary="打招呼",
    response_model = Helloresponse,
    tags=["test"],
)
async def hello(req: HelloRequest):
    return Helloresponse(code="200", message="success")

mcp = FastApiMCP(
    app,
    name="Demo MCP",
    description="示例 MCP 服务",
    include_operations=["say_hello"],  # ⭐⭐⭐ 关键
    describe_all_responses=True,
    describe_full_response_schema=True,
    # include_tags=["test"]
)

mcp.mount_http()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
import filetype

kind = filetype.guess("photo.jpg")
if kind:
    print(kind.mime) 

