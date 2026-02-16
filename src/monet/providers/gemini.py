from __future__ import annotations

from google import genai
from google.genai import types
import base64

from .base import DrawingRequest, DrawingResponse, LLMProvider


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
        # Build content parts — stable prefix first for implicit caching
        parts: list[types.Part] = []

        # 1. Stable text: art prompt
        parts.append(types.Part.from_text(text=f"Art prompt: {request.original_prompt}"))

        # 2. Notes history (grows but prefix is stable — cacheable)
        if request.notes_history:
            notes_text = "\n\n".join(
                f"== Iteration {i + 1} notes ==\n{note}" for i, note in enumerate(request.notes_history)
            )
            parts.append(types.Part.from_text(text=f"Your notes from previous iterations:\n\n{notes_text}"))

        # 3. Canvas image (changes every iteration)
        image_bytes = base64.standard_b64decode(request.canvas_png_base64)
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

        # 4. Current iteration context
        current_lines = [f"Iteration: {request.iteration}", f"Layers: {request.layer_summary}"]
        if not request.notes_history:
            current_lines.append("This is the blank canvas. Begin your artwork.")
        parts.append(types.Part.from_text(text="\n".join(current_lines)))

        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            max_output_tokens=request.max_output_tokens,
        )

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
        return DrawingResponse(
            raw_text=raw_text,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            thinking_tokens=thinking_tokens,
            model=self._model,
        )
