from typing import Generic, TypeVar
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# 泛型类型 T
T = TypeVar("T")


class UploadRequest(BaseModel):
    file_name: str = Field(..., description="文件名称")
    file_data: str = Field(..., description="文件url信息")
    file_class: str = Field(..., description="文件分类的类别")


class SearchRequest(BaseModel):
    file_name: str = Field(..., description="文件名称")
    file_data: str = Field(..., description="文件url信息")
    top_k: int = Field(5, description="文件url信息")
    cosine: float = Field(0.25, description="文件url信息")
