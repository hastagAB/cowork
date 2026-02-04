"""Unified LLM client that dispatches to the configured provider."""

from __future__ import annotations

import os
from typing import AsyncIterator

from cowork.models import AppConfig, LLMConfig


class Message:
    """Simple message container for LLM conversations."""

    def __init__(self, role: str, content: str | None = None, tool_calls: list | None = None,
                 tool_call_id: str | None = None, name: str | None = None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.name = name

    def to_dict(self) -> dict:
        d = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            d["name"] = self.name
        return d


class ToolCall:
    """A tool call requested by the LLM."""

    def __init__(self, id: str, name: str, arguments: dict):
        self.id = id
        self.name = name
        self.arguments = arguments


class LLMResponse:
    """Response from an LLM completion call."""

    def __init__(self, content: str, tokens_used: int = 0, stop_reason: str | None = None,
                 tool_calls: list[ToolCall] | None = None, raw_message: dict | None = None):
        self.content = content
        self.tokens_used = tokens_used
        self.stop_reason = stop_reason
        self.tool_calls = tool_calls or []
        self.raw_message = raw_message  # raw assistant message for conversation history


class LLMClient:
    """Unified LLM client that wraps Anthropic, OpenAI, or Ollama."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    def _get_anthropic_client(self):
        import anthropic

        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
        return self._client

    def _get_openai_client(self):
        import openai

        if self._client is None:
            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def _get_azure_openai_client(self):
        import openai

        if self._client is None:
            api_key = self.config.api_key or os.environ.get("AZURE_OPENAI_API_KEY", "")
            self._client = openai.AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=self.config.endpoint or "",
                api_version=self.config.api_version or "2024-12-01-preview",
            )
        return self._client

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send a completion request to the configured LLM provider."""
        if self.config.provider == "anthropic":
            return await self._complete_anthropic(messages, system, tools)
        elif self.config.provider == "azure_openai":
            return await self._complete_azure_openai(messages, system, tools)
        elif self.config.provider in ("openai", "ollama"):
            return await self._complete_openai(messages, system, tools)
        else:
            raise ValueError(f"Unknown LLM provider: {self.config.provider}")

    async def _complete_anthropic(
        self,
        messages: list[Message],
        system: str | None,
        tools: list[dict] | None,
    ) -> LLMResponse:
        client = self._get_anthropic_client()
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [m.to_dict() for m in messages],
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = await client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        tokens = response.usage.input_tokens + response.usage.output_tokens
        return LLMResponse(
            content=content,
            tokens_used=tokens,
            stop_reason=response.stop_reason,
        )

    async def _complete_openai(
        self,
        messages: list[Message],
        system: str | None,
        tools: list[dict] | None,
    ) -> LLMResponse:
        client = self._get_openai_client()
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(m.to_dict() for m in messages)

        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": msgs,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        tokens = response.usage.total_tokens if response.usage else 0
        return self._parse_openai_response(choice, tokens)

    async def _complete_azure_openai(
        self,
        messages: list[Message],
        system: str | None,
        tools: list[dict] | None,
    ) -> LLMResponse:
        client = self._get_azure_openai_client()
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(m.to_dict() for m in messages)

        # Azure uses deployment name as the model parameter
        model = self.config.deployment or self.config.model
        kwargs = {
            "model": model,
            "max_completion_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": msgs,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        tokens = response.usage.total_tokens if response.usage else 0
        return self._parse_openai_response(choice, tokens)

    def _parse_openai_response(self, choice, tokens: int) -> LLMResponse:
        """Parse an OpenAI/Azure response choice into LLMResponse with tool_calls."""
        import json as _json

        parsed_tool_calls = []
        raw_tool_calls = None

        if choice.message.tool_calls:
            raw_tool_calls = []
            for tc in choice.message.tool_calls:
                args_str = tc.function.arguments or "{}"
                try:
                    args = _json.loads(args_str)
                except _json.JSONDecodeError:
                    args = {}
                parsed_tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
                raw_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args_str,
                    },
                })

        # Build raw_message for conversation history
        raw_msg = {"role": "assistant"}
        if choice.message.content:
            raw_msg["content"] = choice.message.content
        if raw_tool_calls:
            raw_msg["tool_calls"] = raw_tool_calls

        return LLMResponse(
            content=choice.message.content or "",
            tokens_used=tokens,
            stop_reason=choice.finish_reason,
            tool_calls=parsed_tool_calls,
            raw_message=raw_msg,
        )

    async def stream(
        self,
        messages: list[Message],
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion tokens from the LLM."""
        if self.config.provider == "anthropic":
            async for chunk in self._stream_anthropic(messages, system):
                yield chunk
        elif self.config.provider == "azure_openai":
            async for chunk in self._stream_azure_openai(messages, system):
                yield chunk
        elif self.config.provider in ("openai", "ollama"):
            async for chunk in self._stream_openai(messages, system):
                yield chunk

    async def _stream_anthropic(
        self,
        messages: list[Message],
        system: str | None,
    ) -> AsyncIterator[str]:
        client = self._get_anthropic_client()
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [m.to_dict() for m in messages],
        }
        if system:
            kwargs["system"] = system

        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def _stream_openai(
        self,
        messages: list[Message],
        system: str | None,
    ) -> AsyncIterator[str]:
        client = self._get_openai_client()
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(m.to_dict() for m in messages)

        stream = await client.chat.completions.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=msgs,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _stream_azure_openai(
        self,
        messages: list[Message],
        system: str | None,
    ) -> AsyncIterator[str]:
        client = self._get_azure_openai_client()
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(m.to_dict() for m in messages)

        model = self.config.deployment or self.config.model
        stream = await client.chat.completions.create(
            model=model,
            max_completion_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=msgs,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
