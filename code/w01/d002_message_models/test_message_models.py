"""D002 acceptance tests: run against solution.py.

    uv run pytest d002_message_models -q

If you wrote your own starter.py version, swap the import below to test yours:
    from d002_message_models.starter import ...   # noqa
"""

import pytest
from pydantic import ValidationError

from d002_message_models.solution import (
    ChatRequest,
    ChatResponse,
    Choice,
    Message,
    Role,
    ToolCall,
    Usage,
    parse_request,
)


def test_role_behaves_like_a_string():
    assert Role.USER == "user"
    assert Message(role="user", content="hi").role is Role.USER


def test_plain_message_round_trips():
    req = ChatRequest(model="m", messages=[Message(role=Role.USER, content="hi")])
    assert ChatRequest.model_validate(req.to_api_payload()) == req


def test_empty_content_is_rejected():
    with pytest.raises(ValidationError):
        Message(role=Role.USER, content="")


def test_assistant_may_carry_tool_calls_without_content():
    msg = Message(
        role=Role.ASSISTANT,
        tool_calls=[ToolCall(id="c1", name="get_weather", arguments={"city": "Beijing"})],
    )
    assert msg.content is None
    assert msg.tool_calls[0].arguments["city"] == "Beijing"


def test_tool_message_requires_tool_call_id():
    with pytest.raises(ValidationError, match="tool_call_id"):
        Message(role=Role.TOOL, content="done")


def test_empty_messages_list_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(model="m", messages=[])


def test_temperature_string_is_coerced():
    req = ChatRequest(
        model="m",
        messages=[Message(role=Role.USER, content="hi")],
        temperature="0.7",  # type: ignore[arg-type]
    )
    assert req.temperature == 0.7
    assert isinstance(req.temperature, float)


@pytest.mark.parametrize("bad", [-0.1, 2.1, 5.0])
def test_temperature_out_of_range_is_rejected(bad: float):
    with pytest.raises(ValidationError):
        ChatRequest(model="m", messages=[Message(role=Role.USER, content="hi")], temperature=bad)


def test_non_numeric_temperature_string_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(
            model="m",
            messages=[Message(role=Role.USER, content="hi")],
            temperature="hot",  # type: ignore[arg-type]
        )


def test_to_api_payload_drops_none_fields():
    req = ChatRequest(model="m", messages=[Message(role=Role.USER, content="hi")])
    payload = req.to_api_payload()
    assert "max_tokens" not in payload
    assert "tools" not in payload
    assert payload["messages"][0]["role"] == "user"  # enum unwrapped to a plain string


def test_usage_total_tokens():
    assert Usage(prompt_tokens=42, completion_tokens=17).total_tokens == 59


def test_parse_request_returns_readable_error_not_exception():
    result = parse_request({"model": "m", "messages": [{"role": "user", "content": ""}]})
    assert isinstance(result, str)
    assert "invalid request" in result


def test_parse_request_accepts_valid_payload():
    result = parse_request(
        {"model": "m", "messages": [{"role": "user", "content": "hi"}], "temperature": "0.5"}
    )
    assert isinstance(result, ChatRequest)
    assert result.temperature == 0.5


def test_response_shape():
    resp = ChatResponse(
        id="chatcmpl-1",
        model="gpt-4o-mini",
        choices=[
            Choice(
                index=0,
                message=Message(role=Role.ASSISTANT, content="ok"),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=1, completion_tokens=1),
    )
    assert resp.choices[0].finish_reason == "stop"
    assert resp.usage is not None and resp.usage.total_tokens == 2


def test_unknown_finish_reason_is_rejected():
    with pytest.raises(ValidationError):
        Choice(
            index=0,
            message=Message(role=Role.ASSISTANT, content="ok"),
            finish_reason="whatever",
        )
