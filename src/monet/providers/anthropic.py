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
        return "claude-sonnet-4-5-20250929"

    def send_drawing_request(self, request: DrawingRequest) -> DrawingResponse:
        system = [
            {
                "type": "text",
                "text": request.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        user_parts: list[dict] = []

        # 1. Stable text: art prompt (prefix-cacheable)
        user_parts.append({"type": "text", "text": f"Art prompt: {request.original_prompt}"})

        # 2. Notes history (grows but prefix is stable — cacheable)
        if request.notes_history:
            notes_text = "\n\n".join(
                f"== Iteration {i + 1} notes ==\n{note}" for i, note in enumerate(request.notes_history)
            )
            user_parts.append({
                "type": "text",
                "text": f"Your notes from previous iterations:\n\n{notes_text}",
                "cache_control": {"type": "ephemeral"},
            })

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
        current_lines = [f"Iteration: {request.iteration}", f"Layers: {request.layer_summary}"]
        if not request.notes_history:
            current_lines.append("This is the blank canvas. Begin your artwork.")
        user_parts.append({"type": "text", "text": "\n".join(current_lines)})

        kwargs: dict = {
            "model": self._model,
            "max_tokens": request.max_output_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_parts}],
        }

        if request.thinking_enabled:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": request.thinking_budget,
            }

        response = self._client.messages.create(**kwargs)

        # Extract text from response blocks
        raw_text = ""
        thinking_tokens = 0
        for block in response.content:
            if block.type == "text":
                raw_text += block.text
            elif block.type == "thinking":
                thinking_tokens += getattr(block, "tokens", 0)

        usage = response.usage
        return DrawingResponse(
            raw_text=raw_text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            thinking_tokens=thinking_tokens,
            model=response.model,
        )
