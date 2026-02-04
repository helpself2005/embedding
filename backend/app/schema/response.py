from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# 泛型类型 T
T = TypeVar("T")


class ApiResponse(
    BaseModel,
):
    """通用 API 响应格式"""
    code: int = Field(200, title="状态码")
    msg: str = Field("", title="提示信息")
    data: Any = Field(None, title="返回结果数据")
