from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=16_000)


class MessageBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    messages: list[ChatMessage] = Field(min_length=1, max_length=128)
