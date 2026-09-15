"""D002 reference solution: typed models for an LLM gateway.

Mirrors the real request/response shape of OpenAI / DeepSeek / Qwen chat APIs.

Run:   uv run python d002_message_models/solution.py
Test:  uv run pytest d002_message_models -q
"""

from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)


class Role(StrEnum):
    """`StrEnum` (3.11+) keeps values JSON-serializable and comparable to plain strings.

    Older codebases use `class Role(str, Enum)` for pre-3.11 compatibility -
    you will see both in the wild; StrEnum is the modern spelling.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """A single tool invocation requested by the model."""

    id: str
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    """A tool the model is allowed to call (function-calling schema)."""

    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: Role
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

    @model_validator(mode="after")
    def _check_payload(self) -> "Message":
        if self.role is Role.TOOL:
            if not self.tool_call_id:
                raise ValueError("a tool message must carry tool_call_id")
            return self
        if not self.content and not self.tool_calls:
            raise ValueError("message needs either content or tool_calls")
        return self


class Usage(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)

    # `@computed_field` puts this property into model_dump() output.
    # Without it a plain @property is invisible to serialization - a classic gotcha.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class Choice(BaseModel):
    index: int = Field(ge=0)
    message: Message
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"] | None = None


class ChatRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[Message] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    tools: list[ToolSpec] | None = None

    @field_validator("temperature", mode="before")
    @classmethod
    def _coerce_temperature(cls, v: Any) -> Any:
        """Legacy clients love sending numbers as strings. Accept "0.7" as 0.7."""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError as exc:
                raise ValueError(f"temperature must be numeric, got {v!r}") from exc
        return v

    def to_api_payload(self) -> dict[str, Any]:
        """Payload for the upstream API: drop None fields, unwrap enums to plain strings."""
        return self.model_dump(exclude_none=True, mode="json")


class ChatResponse(BaseModel):
    id: str
    model: str
    choices: list[Choice] = Field(min_length=1)
    usage: Usage | None = None


def parse_request(raw: dict[str, Any]) -> ChatRequest | str:
    """Parse untrusted input. Returns the model on success, a readable message on failure.

    FDE habit: never leak a raw traceback to a client. Give back something they can act on.
    """
    try:
        return ChatRequest.model_validate(raw)
    except ValidationError as exc:
        lines = [
            f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in exc.errors()
        ]
        return "invalid request: " + "; ".join(lines)


def main() -> None:
    print("=== 1. build a request ===")
    req = ChatRequest(
        model="gpt-4o-mini",
        messages=[
            Message(role=Role.SYSTEM, content="You are a precise assistant."),
            Message(role=Role.USER, content="What is the weather in Beijing?"),
        ],
    )
    print(req.to_api_payload())

    print("\n=== 2. temperature given as a string ===")
    req2 = ChatRequest(
        model="gpt-4o-mini",
        messages=[Message(role=Role.USER, content="hi")],
        temperature="0.7",  # type: ignore[arg-type]  # legacy clients do this
    )
    print(f"temperature = {req2.temperature!r} ({type(req2.temperature).__name__})")

    print("\n=== 3. round trip: model -> dict -> model ===")
    restored = ChatRequest.model_validate(req.to_api_payload())
    print(f"equal: {restored == req}")

    print("\n=== 4. reject an empty message ===")
    print(parse_request({"model": "m", "messages": [{"role": "user", "content": ""}]}))

    print("\n=== 5. reject a tool message without tool_call_id ===")
    print(parse_request({"model": "m", "messages": [{"role": "tool", "content": "done"}]}))

    print("\n=== 6. reject out-of-range temperature ===")
    print(
        parse_request(
            {"model": "m", "messages": [{"role": "user", "content": "hi"}], "temperature": 5.0}
        )
    )

    print("\n=== 7. a tool-calling exchange ===")
    resp = ChatResponse(
        id="chatcmpl-1",
        model="gpt-4o-mini",
        choices=[
            Choice(
                index=0,
                message=Message(
                    role=Role.ASSISTANT,
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_1", name="get_weather", arguments={"city": "Beijing"})
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=42, completion_tokens=17),
    )
    call = resp.choices[0].message.tool_calls[0]
    total = resp.usage.total_tokens if resp.usage else 0
    print(f"tool={call.name} args={call.arguments} total_tokens={total}")


if __name__ == "__main__":
    main()
