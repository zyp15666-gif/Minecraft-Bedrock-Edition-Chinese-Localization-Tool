#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 本地模型提供商
"""

import os
from typing import Any, Dict, Optional, Tuple

from .base import BaseProvider


class OllamaProvider(BaseProvider):
    """本地 Ollama 提供商"""

    PROVIDER_TYPE = "local_ollama"

    def build_request(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        is_test: bool = False
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        headers = {"Content-Type": "application/json"}

        api_key = self._get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if system_prompt:
            user_content = system_prompt
        else:
            user_content = text

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_content}
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": 512,
            }
        }
        api_url = self.api_config.get("api_url", "")
        return api_url, headers, payload

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        if "choices" in response_data:
            choices = response_data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "")
                if content and content.strip():
                    return content.strip()
        if "message" in response_data:
            return response_data["message"]["content"].strip()
        elif "content" in response_data:
            return response_data["content"].strip()
        return ""

    def _get_api_key(self) -> str:
        api_key = self.api_config.get("api_key", "")
        if not api_key or any(kw in api_key.lower() for kw in ['你的', 'your', 'your_key']):
            env_key = os.environ.get(f"API_KEY_{self.name.upper().replace(' ', '_')}", "")
            if env_key:
                return env_key
        return api_key

    def validate_config(self) -> bool:
        return bool(self.api_config.get("api_url") and self.api_config.get("model"))
