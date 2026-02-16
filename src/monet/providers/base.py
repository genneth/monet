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
    thinking_enabled: bool = False
    thinking_budget: int = 4096


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
