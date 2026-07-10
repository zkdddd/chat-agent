from types import SimpleNamespace

from kagent.agent.agent_stream import aggregate_chat_completion_stream


def test_aggregate_stream_emits_text_deltas():
    emitted = []
    stream = [
        _chunk(content="Hel"),
        _chunk(content="lo"),
    ]

    message = aggregate_chat_completion_stream(stream, on_text_delta=emitted.append)

    assert message.content == "Hello"
    assert emitted == ["Hel", "lo"]
    assert message.tool_calls == []
    assert message.model_dump() == {"role": "assistant", "content": "Hello"}


def test_aggregate_stream_collects_tool_call_arguments_before_execution():
    stream = [
        _chunk(
            tool_calls=[
                _tool_delta(
                    index=0,
                    call_id="call-1",
                    name="read_file",
                    arguments='{"path"',
                )
            ]
        ),
        _chunk(tool_calls=[_tool_delta(index=0, arguments=':"README.md"}')]),
    ]

    message = aggregate_chat_completion_stream(stream)

    assert message.content == ""
    assert len(message.tool_calls) == 1
    call = message.tool_calls[0]
    assert call.id == "call-1"
    assert call.type == "function"
    assert call.function.name == "read_file"
    assert call.function.arguments == '{"path":"README.md"}'
    assert message.model_dump() == {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path":"README.md"}',
                },
            }
        ],
    }


def test_aggregate_stream_keeps_multiple_tool_call_indexes_ordered():
    stream = [
        _chunk(
            tool_calls=[
                _tool_delta(index=1, call_id="call-2", name="run_command", arguments='{"command":"pytest"}'),
                _tool_delta(index=0, call_id="call-1", name="read_file", arguments='{"path":"a.py"}'),
            ]
        )
    ]

    message = aggregate_chat_completion_stream(stream)

    assert [call.id for call in message.tool_calls] == ["call-1", "call-2"]
    assert [call.function.name for call in message.tool_calls] == ["read_file", "run_command"]


def _chunk(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls,
                )
            )
        ]
    )


def _tool_delta(index, call_id=None, name=None, arguments=None):
    return SimpleNamespace(
        index=index,
        id=call_id,
        type="function" if call_id else None,
        function=SimpleNamespace(
            name=name,
            arguments=arguments,
        ),
    )
