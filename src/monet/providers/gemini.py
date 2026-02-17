from __future__ import annotations

import base64

from google import genai
from google.genai import types

from .base import DrawingRequest, DrawingResponse, LLMProvider


def _format_token_details(details: object) -> str:
    """Format a token details object (list of ModalityTokenCount or similar) for logging."""
    if not details:
        return ""
    # Details may be a list of objects with modality/token_count attrs, or something else.
    # Log whatever we get for visibility.
    if isinstance(details, list):
        parts = []
        for entry in details:
            modality = getattr(entry, "modality", None)
            token_count = getattr(entry, "token_count", None)
            if modality and token_count:
                parts.append(f"{modality}={token_count}")
            else:
                parts.append(str(entry))
        return ", ".join(parts)
    return str(details)


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

    def send_drawing_request(self, request: DrawingRequest) -> DrawingResponse:
        provider_log: list[str] = []

        # Build content parts — stable prefix first for implicit caching.
        # Gemini automatically caches repeated prefixes across requests.
        parts: list[types.Part] = []

        # 1. Stable text: art prompt (prefix-cacheable)
        parts.append(types.Part.from_text(text=f"Art prompt: {request.original_prompt}"))

        # 2. Notes history (grows but prefix is stable — cacheable)
        if request.notes_history:
            notes_text = "\n\n".join(request.format_notes())
            parts.append(types.Part.from_text(text=f"Your notes from previous iterations:\n\n{notes_text}"))

        # 3. Canvas image (changes every iteration — never cached)
        image_bytes = base64.standard_b64decode(request.canvas_png_base64)
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

        # 4. Current iteration context (changes every iteration)
        parts.append(types.Part.from_text(text=request.format_context_lines()))

        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            max_output_tokens=request.max_output_tokens,
        )

        if request.thinking_enabled:
            config.thinking_config = types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.HIGH,
            )
        else:
            config.thinking_config = types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )

        response = self._client.models.generate_content(
            model=self._model,
            contents=parts,
            config=config,
        )

        raw_text = ""
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if not part.thought:
                    raw_text += part.text

        # Extract token counts from usage metadata
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_token_count = getattr(usage, "candidates_token_count", 0) or 0
        cached_token_count = getattr(usage, "cached_content_token_count", 0) or 0
        thinking_tokens = getattr(usage, "thoughts_token_count", 0) or 0

        # Log cache status
        if cached_token_count:
            provider_log.append(f"Cache hit: {cached_token_count}/{prompt_tokens} input tokens from cache")
        else:
            provider_log.append("No cache hit")

        # Log thinking tokens
        if thinking_tokens:
            provider_log.append(f"Thinking: {thinking_tokens} tokens")

        # Log token details breakdowns if available
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        if prompt_details:
            provider_log.append(f"Prompt details: [{_format_token_details(prompt_details)}]")

        cache_details = getattr(usage, "cache_tokens_details", None)
        if cache_details:
            provider_log.append(f"Cache details: [{_format_token_details(cache_details)}]")

        candidates_details = getattr(usage, "candidates_tokens_details", None)
        if candidates_details:
            provider_log.append(f"Output details: [{_format_token_details(candidates_details)}]")

        return DrawingResponse(
            raw_text=raw_text,
            input_tokens=prompt_tokens,
            output_tokens=output_token_count,
            cache_read_tokens=cached_token_count,
            thinking_tokens=thinking_tokens,
            model=self._model,
            provider_log=provider_log,
        )
