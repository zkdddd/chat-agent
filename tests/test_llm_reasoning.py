from kagent import llm


def test_chat_completion_retries_without_unsupported_reasoning(monkeypatch):
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if "reasoning_effort" in kwargs:
                raise ValueError("unsupported parameter: reasoning_effort")
            return "ok"

    class FakeClient:
        class Chat:
            completions = FakeCompletions()

        chat = Chat()

    monkeypatch.setattr(llm, "client", FakeClient())

    result = llm.create_chat_completion_with_reasoning(
        model="gpt-5.5",
        messages=[{"role": "user", "content": "hi"}],
        reasoning_effort="high",
    )

    assert result == "ok"
    assert calls[0]["reasoning_effort"] == "high"
    assert "reasoning_effort" not in calls[1]


def test_open_chat_stream_includes_runtime_metadata(monkeypatch):
    captured = {}

    class FakeStream:
        def close(self):
            pass

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeStream()

    monkeypatch.setattr(llm.client.chat.completions, "create", fake_create)

    llm.open_chat_stream(
        [{"role": "user", "content": "what model are you using?"}],
        model="gpt-5.5",
        reasoning_effort="high",
    )

    system_text = "\n\n".join(
        message["content"]
        for message in captured["messages"]
        if message.get("role") == "system"
    )
    assert captured["model"] == "gpt-5.5"
    assert "Current runtime model: gpt-5.5" in system_text
    assert "Current reasoning effort: high" in system_text
