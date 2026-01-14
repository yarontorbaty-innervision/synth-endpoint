"""
VLM Client - Unified interface for vision language models.
"""

from __future__ import annotations
import base64
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, List

from PIL import Image

logger = logging.getLogger(__name__)


class VLMProvider(str, Enum):
    """Supported VLM providers."""
    OLLAMA = "ollama"  # Local - LLaVA, Qwen-VL, etc.
    OPENAI = "openai"  # GPT-4V, GPT-4o
    GEMINI = "gemini"  # Gemini Pro Vision


@dataclass
class VLMConfig:
    """Configuration for VLM client."""
    provider: VLMProvider = VLMProvider.OLLAMA
    model: str = "llava:13b"  # Default to LLaVA 13B for local
    api_key: Optional[str] = None
    base_url: str = "http://localhost:11434"  # Ollama default
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 120
    
    @classmethod
    def local(cls, model: str = "llava:13b") -> VLMConfig:
        """Create config for local Ollama model."""
        return cls(provider=VLMProvider.OLLAMA, model=model)
    
    @classmethod
    def openai(cls, api_key: str, model: str = "gpt-4o") -> VLMConfig:
        """Create config for OpenAI."""
        return cls(provider=VLMProvider.OPENAI, model=model, api_key=api_key)
    
    @classmethod
    def gemini(cls, api_key: str, model: str = "gemini-1.5-pro") -> VLMConfig:
        """Create config for Google Gemini."""
        return cls(provider=VLMProvider.GEMINI, model=model, api_key=api_key)


class BaseVLMClient(ABC):
    """Abstract base class for VLM clients."""
    
    @abstractmethod
    async def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Analyze an image with a text prompt."""
        pass
    
    @abstractmethod
    async def analyze_images(self, images: List[Image.Image], prompt: str) -> str:
        """Analyze multiple images with a text prompt."""
        pass
    
    def image_to_base64(self, image: Image.Image, format: str = "JPEG") -> str:
        """Convert PIL Image to base64 string."""
        buffer = BytesIO()
        image.save(buffer, format=format, quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


class OllamaClient(BaseVLMClient):
    """Client for Ollama (local VLM)."""
    
    def __init__(self, config: VLMConfig):
        self.config = config
        self.base_url = config.base_url
        self.model = config.model
    
    async def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Analyze image using Ollama."""
        import httpx
        
        # Convert image to base64
        image_b64 = self.image_to_base64(image)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    
    async def analyze_images(self, images: List[Image.Image], prompt: str) -> str:
        """Analyze multiple images using Ollama."""
        import httpx
        
        # Convert all images to base64
        images_b64 = [self.image_to_base64(img) for img in images]
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": images_b64,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")


class OpenAIClient(BaseVLMClient):
    """Client for OpenAI GPT-4V/GPT-4o."""
    
    def __init__(self, config: VLMConfig):
        self.config = config
        self.api_key = config.api_key
        self.model = config.model
    
    async def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Analyze image using OpenAI."""
        import httpx
        
        image_b64 = self.image_to_base64(image)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def analyze_images(self, images: List[Image.Image], prompt: str) -> str:
        """Analyze multiple images using OpenAI."""
        import httpx
        
        content = [{"type": "text", "text": prompt}]
        
        for img in images:
            image_b64 = self.image_to_base64(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}",
                    "detail": "high"
                }
            })
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]


class GeminiClient(BaseVLMClient):
    """Client for Google Gemini."""
    
    def __init__(self, config: VLMConfig):
        self.config = config
        self.api_key = config.api_key
        self.model = config.model
    
    async def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Analyze image using Gemini."""
        import httpx
        
        image_b64 = self.image_to_base64(image)
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
    
    async def analyze_images(self, images: List[Image.Image], prompt: str) -> str:
        """Analyze multiple images using Gemini."""
        import httpx
        
        parts = [{"text": prompt}]
        
        for img in images:
            image_b64 = self.image_to_base64(img)
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_b64
                }
            })
        
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]


class VLMClient:
    """
    Unified VLM client that supports multiple providers.
    
    Usage:
        # Local with Ollama
        client = VLMClient(VLMConfig.local("llava:13b"))
        
        # OpenAI
        client = VLMClient(VLMConfig.openai(api_key="..."))
        
        # Gemini
        client = VLMClient(VLMConfig.gemini(api_key="..."))
    """
    
    def __init__(self, config: Optional[VLMConfig] = None):
        self.config = config or VLMConfig()
        self._client = self._create_client()
    
    def _create_client(self) -> BaseVLMClient:
        """Create the appropriate client based on provider."""
        if self.config.provider == VLMProvider.OLLAMA:
            return OllamaClient(self.config)
        elif self.config.provider == VLMProvider.OPENAI:
            return OpenAIClient(self.config)
        elif self.config.provider == VLMProvider.GEMINI:
            return GeminiClient(self.config)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
    
    async def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Analyze a single image with a prompt."""
        return await self._client.analyze_image(image, prompt)
    
    async def analyze_images(self, images: List[Image.Image], prompt: str) -> str:
        """Analyze multiple images with a prompt."""
        return await self._client.analyze_images(images, prompt)
    
    @staticmethod
    def check_ollama_available(base_url: str = "http://localhost:11434") -> bool:
        """Check if Ollama is running locally."""
        import httpx
        try:
            response = httpx.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    @staticmethod
    def list_ollama_models(base_url: str = "http://localhost:11434") -> List[str]:
        """List available Ollama models."""
        import httpx
        try:
            response = httpx.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []
