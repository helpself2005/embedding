from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# 泛型类型 T
T = TypeVar("T")

class SearchResponse(BaseModel, ):
    code: int = Field(200, title="成功标识")
    msg: str = Field("", title="提示信息")
    data: Any =  Field(None, title="返回结果数据")