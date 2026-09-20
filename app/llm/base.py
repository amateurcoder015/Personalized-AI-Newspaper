from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """Abstract interface for replaceable LLM Providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text response from prompt."""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON dictionary response conforming to schema."""
        pass
