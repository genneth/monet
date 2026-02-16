from __future__ import annotations

import base64

from google import genai
from google.genai import types

from .base import DrawingRequest, DrawingResponse, LLMProvider

CACHE_TTL = "1200s"  # 20 minutes


class GeminiProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self._model = model or self.default_model
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-3-flash-preview"

    def _build_cached_contents(self, request: DrawingRequest) -> list[types.Content]:
        """Build the stable content parts that should be cached (art prompt + notes history)."""
        parts: list[types.Part] = []
        parts.append(types.Part.from_text(text=f"Art prompt: {request.original_prompt}"))
        if request.notes_history:
            notes_text = "\n\n".join(
                f"== Iteration {i + 1} notes ==\n{note}" for i, note in enumerate(request.notes_history)
            )
            parts.append(types.Part.from_text(text=f"Your notes from previous iterations:\n\n{notes_text}"))
        return [types.Content(role="user", parts=parts)]

    def send_drawing_request(self, request: DrawingRequest) -> DrawingResponse:
        provider_log: list[str] = []

        # Try to create cache with stable content
        cache_name = None
        try:
            cache = self._client.caches.create(
                model=self._model,
                config=types.CreateCachedContentConfig(
                    system_instruction=request.system_prompt,
                    contents=self._build_cached_contents(request),
                    ttl=CACHE_TTL,
                ),
            )
            cache_name = cache.name
            provider_log.append(f"Cache created: {cache_name}")
        except Exception as e:
            provider_log.append(f"Cache creation failed (proceeding without): {e}")

        # Build per-request content (image + current iteration context)
        parts: list[types.Part] = []

        if not cache_name:
            # Cache failed — include everything inline
            parts.append(types.Part.from_text(text=f"Art prompt: {request.original_prompt}"))
            if request.notes_history:
                notes_text = "\n\n".join(
                    f"== Iteration {i + 1} notes ==\n{note}" for i, note in enumerate(request.notes_history)
                )
                parts.append(types.Part.from_text(text=f"Your notes from previous iterations:\n\n{notes_text}"))

        # Canvas image (always per-request, never cached)
        image_bytes = base64.standard_b64decode(request.canvas_png_base64)
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

        # Current iteration context
        current_lines = [f"Iteration: {request.iteration}", f"Layers: {request.layer_summary}"]
        if not request.notes_history:
            current_lines.append("This is the blank canvas. Begin your artwork.")
        parts.append(types.Part.from_text(text="\n".join(current_lines)))

        config = types.GenerateContentConfig(
            max_output_tokens=request.max_output_tokens,
        )

        if cache_name:
            config.cached_content = cache_name
        else:
            config.system_instruction = request.system_prompt

        if request.thinking_enabled:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=request.thinking_budget,
            )

        response = self._client.models.generate_content(
            model=self._model,
            contents=parts,
            config=config,
        )

        raw_text = ""
        thinking_tokens = 0
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.thought:
                    thinking_tokens += len(part.text) // 4  # rough estimate
                else:
                    raw_text += part.text

        usage = response.usage_metadata
        cached_token_count = getattr(usage, "cached_content_token_count", 0) or 0
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_token_count = getattr(usage, "candidates_token_count", 0) or 0

        if cached_token_count:
            provider_log.append(f"Cache hit: {cached_token_count}/{prompt_tokens} input tokens from cache")
        elif cache_name:
            provider_log.append("Cache created but no tokens read from it (unexpected)")

        return DrawingResponse(
            raw_text=raw_text,
            input_tokens=prompt_tokens,
            output_tokens=output_token_count,
            cache_read_tokens=cached_token_count,
            thinking_tokens=thinking_tokens,
            model=self._model,
            provider_log=provider_log,
        )
