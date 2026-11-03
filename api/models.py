"""HTTP输入结构；模型适用性和金融参数由计算适配层校验。"""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Body(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ExampleBody(Body):
    example_id: str


class PrepareBody(Body):
    metadata: dict[str, Any] | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class NameBody(Body):
    name: str = Field(min_length=1, max_length=128)

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError('名称不能为空')
        return value.strip()


class SavePreviewBody(NameBody):
    metadata: dict[str, Any] | None = None
    description: str = Field(default='', max_length=10000)


class UpdateBody(Body):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    archived: bool | None = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, value):
        return NameBody.name_not_blank(value) if value is not None else None


class JobBody(Body):
    dataset_id: str
    operation: str = Field(min_length=1, max_length=100)
    parameters: dict[str, Any] = Field(default_factory=dict)
