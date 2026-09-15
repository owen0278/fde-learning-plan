"""D002 starter: fill in the TODOs, then compare against solution.py.

Rules worth remembering while you write:
  - `field_validator`  -> validate / coerce ONE field   (mode="before" sees the raw input)
  - `model_validator`  -> validate the WHOLE model      (mode="after" sees the built object)
  - `Field(ge=, le=, min_length=)` -> declarative constraints, no hand-written ifs

Convention used below: field declarations are given (they are declarative and easy).
Everything that requires a decision is left for you as `raise NotImplementedError`.
"""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """TODO 1: id: str, name: str (non-empty), arguments: dict[str, Any] defaulting to {}

    Hint: mutable defaults must use `Field(default_factory=dict)`, never `= {}`.
    """

    id: str
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    """TODO 2: name: str (non-empty), description: str default "", parameters: dict default {}"""

    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: Role
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

    # TODO 3: add `@model_validator(mode="after")`, then:
    #   - role == Role.TOOL  -> require tool_call_id, else raise ValueError
    #   - any other role     -> require content OR tool_calls, else raise ValueError
    # Must `return self` at the end.
    @model_validator(mode="after")
    def _check_payload(self) -> "Message":
        raise NotImplementedError("TODO 3")


class Usage(BaseModel):
    """TODO 4: prompt_tokens / completion_tokens, both >= 0, plus a total_tokens property.

    Gotcha to discover: a bare @property does NOT show up in model_dump().
    If you want it serialized, stack `@computed_field` above `@property`
    (see solution.py - the import is from pydantic).
    """

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)

    @property
    def total_tokens(self) -> int:
        raise NotImplementedError("TODO 4")


class Choice(BaseModel):
    """TODO 5: index >= 0, message: Message, finish_reason limited to 4 literals or None."""

    index: int = Field(ge=0)
    message: Message
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"] | None = None


class ChatRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[Message] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    tools: list[ToolSpec] | None = None

    # TODO 6: `@field_validator("temperature", mode="before")`
    #   str -> float. If float() raises, raise ValueError naming the bad value.
    @field_validator("temperature", mode="before")
    @classmethod
    def _coerce_temperature(cls, v: Any) -> Any:
        raise NotImplementedError("TODO 6")

    # TODO 7 (L2): return self.model_dump(exclude_none=True, mode="json")
    #   exclude_none drops null fields the upstream API would reject.
    def to_api_payload(self) -> dict[str, Any]:
        raise NotImplementedError("TODO 7")


class ChatResponse(BaseModel):
    id: str
    model: str
    choices: list[Choice] = Field(min_length=1)
    usage: Usage | None = None


# TODO 8 (L2): parse_request(raw) -> ChatRequest | str
#   success -> the model
#   ValidationError -> one readable line built from `exc.errors()` (each has "loc" and "msg")
def parse_request(raw: dict[str, Any]) -> ChatRequest | str:
    raise NotImplementedError("TODO 8")


if __name__ == "__main__":
    req = ChatRequest(
        model="gpt-4o-mini",
        messages=[Message(role=Role.USER, content="hello")],
        temperature="0.7",  # type: ignore[arg-type]  # legacy clients send strings
    )
    print(req.to_api_payload())
    print(parse_request({"model": "m", "messages": [{"role": "user", "content": ""}]}))
