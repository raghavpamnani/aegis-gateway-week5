from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Investigation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=8, max_length=1500)
    scenario: Literal["healthy", "timeout", "rate_limit", "outage", "midstream"] = "healthy"
    cache: bool = True
    baseline: bool = False


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[A-Z]+-\d{3}$")
    title: str = Field(min_length=3)
    body: str = Field(min_length=20, max_length=6000)
    version: int = Field(ge=1)
    category: Literal["policy", "runbook"]
    cacheable: bool = False


class Event(BaseModel):
    type: str
    data: dict
