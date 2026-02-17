from __future__ import annotations

import anthropic

from .base import DrawingRequest, DrawingResponse, LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self._model = model or self.default_model
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-6"

    def send_drawing_request(self, request: DrawingRequest) -> DrawingResponse:
        provider_log: list[str] = []

        system = [
            {
                "type": "text",
                "text": request.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        user_parts: list[dict] = []

        # 1. Stable text: art prompt (prefix-cacheable, breakpoint 2 of 4)
        user_parts.append(
            {
                "type": "text",
                "text": f"Art prompt: {request.original_prompt}",
                "cache_control": {"type": "ephemeral"},
            }
        )

        # 2. Notes history — each note as its own content block for incremental caching.
        #    Anthropic allows max 4 cache breakpoints. We use:
        #      1. System prompt (always)
        #      2. Art prompt (always)
        #      3. Second-to-last note (matches previous call's last-note cache → read)
        #      4. Last note (creates cache for next call)
        if request.notes_history:
            note_texts = request.format_notes()
            note_blocks: list[dict] = []
            for i, text in enumerate(note_texts):
                prefix = "Your notes from previous iterations:\n\n" if i == 0 else ""
                note_blocks.append({"type": "text", "text": f"{prefix}{text}"})
            # Cache breakpoints on last 2 notes (breakpoints 3-4 of max 4).
            if len(note_blocks) >= 2:
                note_blocks[-2]["cache_control"] = {"type": "ephemeral"}
            note_blocks[-1]["cache_control"] = {"type": "ephemeral"}
            user_parts.extend(note_blocks)

        # 3. Canvas image (changes every iteration — never cached)
        user_parts.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": request.canvas_png_base64,
                },
            }
        )

        # 4. Current iteration context (changes every iteration)
        user_parts.append({"type": "text", "text": request.format_context_lines()})

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 16_000 if request.thinking_enabled else request.max_output_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_parts}],
        }

        if request.thinking_enabled:
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": "high"}
            provider_log.append("Adaptive thinking enabled (effort=high)")

        response = self._client.messages.create(**kwargs)

        # Extract text from response blocks.
        # ThinkingBlock has .thinking (str) and .signature, but no token count.
        # Claude 4 returns summarised thinking; billed tokens (in usage.output_tokens)
        # include the full thinking cost, so we estimate from the summary text.
        raw_text = ""
        thinking_tokens = 0
        for block in response.content:
            if block.type == "text":
                raw_text += block.text
            elif block.type == "thinking":
                thinking_tokens += len(block.thinking) // 4  # rough char-to-token estimate

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0

        if cache_read:
            provider_log.append(f"Cache hit: {cache_read}/{usage.input_tokens} input tokens from cache")
        elif cache_create:
            provider_log.append(f"Cache primed: {cache_create} tokens written to cache")

        if thinking_tokens:
            provider_log.append(
                f"Thinking: ~{thinking_tokens} summary tokens (billed as part of {usage.output_tokens} output tokens)"
            )

        return DrawingResponse(
            raw_text=raw_text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_create,
            thinking_tokens=thinking_tokens,
            model=response.model,
            provider_log=provider_log,
        )
