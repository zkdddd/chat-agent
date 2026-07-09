import os
from typing import Iterator

from openai import OpenAI, Stream

from .config import (
    CONTEXT_KEEP_RECENT_MESSAGES,
    CONTEXT_MAX_TOKENS,
    CONTEXT_PER_MESSAGE_MAX_CHARS,
    CONTEXT_SUMMARY_MAX_CHARS,
    MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    SYSTEM_PROMPT,
)
from .context import manage_context

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
CHAT_REQUEST_TIMEOUT_SECONDS = float(os.getenv("KAGENT_CHAT_TIMEOUT_SECONDS", "45"))
STREAM_REQUEST_TIMEOUT_SECONDS = float(
    os.getenv("KAGENT_STREAM_TIMEOUT_SECONDS", str(CHAT_REQUEST_TIMEOUT_SECONDS))
)
TITLE_REQUEST_TIMEOUT_SECONDS = float(os.getenv("KAGENT_TITLE_TIMEOUT_SECONDS", "10"))
AGENT_REQUEST_TIMEOUT_SECONDS = float(
    os.getenv("KAGENT_AGENT_TIMEOUT_SECONDS", str(CHAT_REQUEST_TIMEOUT_SECONDS))
)


def open_chat_stream(
    messages: list[dict],
    timeout: float | None = STREAM_REQUEST_TIMEOUT_SECONDS,
) -> Stream:
    full = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    full, _ = manage_context(
        full,
        max_tokens=CONTEXT_MAX_TOKENS,
        keep_recent_messages=CONTEXT_KEEP_RECENT_MESSAGES,
        summary_max_chars=CONTEXT_SUMMARY_MAX_CHARS,
        per_message_max_chars=CONTEXT_PER_MESSAGE_MAX_CHARS,
    )
    return client.chat.completions.create(
        model=MODEL,
        messages=full,
        stream=True,
        temperature=0.7,
        timeout=timeout,
    )


def stream_chat(messages: list[dict]) -> Iterator[str]:
    """同步流式调用 OpenAI Chat Completions，逐段 yield 文本。

    供 QThread worker 调用：阻塞迭代，UI 线程通过 signal 接收 chunk。
    """
    stream = open_chat_stream(messages)
    try:
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    finally:
        stream.close()


def generate_title(
    first_user_msg: str,
    timeout: float | None = TITLE_REQUEST_TIMEOUT_SECONDS,
) -> str:
    """根据首条用户消息生成会话标题（4-12 字）。"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "根据用户消息生成一个简洁的中文会话标题，4-12 个字，不要标点。",
                },
                {"role": "user", "content": first_user_msg},
            ],
            temperature=0.3,
            max_tokens=32,
            timeout=timeout,
        )
        title = (resp.choices[0].message.content or "").strip().strip("\"'""''")
        return title[:20] if title else "新对话"
    except Exception:
        return "新对话"
