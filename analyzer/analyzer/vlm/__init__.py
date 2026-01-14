"""
Vision Language Model (VLM) integration for video analysis.

Supports multiple backends:
- Local: Ollama with LLaVA, Qwen-VL
- Cloud: OpenAI GPT-4V, Google Gemini
"""

from analyzer.vlm.client import VLMClient, VLMConfig
from analyzer.vlm.analyzer import VLMAnalyzer

__all__ = ["VLMClient", "VLMConfig", "VLMAnalyzer"]
