from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DrawingRequest:
    system_prompt: str
    canvas_png_base64: str
    original_prompt: str
    iteration: int
    layer_summary: str
    notes_history: list[str] = field(default_factory=list)
    max_output_tokens: int = 4096
    iteration_message: str | None = None
    thinking_enabled: bool = False
    thinking_budget: int = 4096

    def format_notes(self) -> list[str]:
        """Return formatted note strings, one per iteration."""
        return [f"== Iteration {i + 1} notes ==\n{note}" for i, note in enumerate(self.notes_history)]

    def format_context_lines(self) -> str:
        """Return the current-iteration context text."""
        lines = [f"Iteration: {self.iteration}", f"Layers: {self.layer_summary}"]
        if self.iteration_message:
            lines.append(self.iteration_message)
        elif not self.notes_history:
            lines.append("This is the blank canvas. Begin your artwork.")
        if self.notes_history:
            lines.append("If your notes are repeating similar ideas, move on to the next stage or set status to done.")
        return "\n".join(lines)


@dataclass
class DrawingResponse:
    raw_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    thinking_tokens: int = 0
    model: str = ""
    provider_log: list[str] = field(default_factory=list)


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    def send_drawing_request(self, request: DrawingRequest) -> DrawingResponse: ...
