from typing import Generic, TypeVar
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# 泛型类型 T
T = TypeVar("T")


class OneImageUploadDTO(BaseModel):
    file_name: str = ""
    file_data: bytes = b""
    file_type: str = ""
    file_class: str = "test"


class OneImageSearchDTO(BaseModel):
    file_name: str = ""
    file_data: bytes = b""
    file_type: str = ""
    top_k: int = 5
    cosine: float = 0.25
