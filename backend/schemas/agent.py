from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=24)


class SuggestionRequest(BaseModel):
    question: str = Field(default="", max_length=2000)
    answer: str = Field(default="", max_length=4000)
    page: str = Field(default="", max_length=200)
    experiment_done: bool | None = None
