#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI 兼容格式提供商（DeepSeek、Qwen等）
"""

import os
from typing import Any, Dict, Optional, Tuple

from .base import BaseProvider


class OpenAICompatibleProvider(BaseProvider):
    """OpenAI 兼容格式提供商（DeepSeek、Qwen等）"""

    PROVIDER_TYPE = "openai_compatible"

    def build_request(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        is_test: bool = False
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        if system_prompt is None:
            system_prompt = "你是一个专业的 Minecraft 汉化专家，负责将英文文本翻译成中文。请保持专业术语的一致性，确保翻译准确、流畅。"

        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": self.temperature,
        }
        api_url = self.api_config["api_url"]
        return api_url, headers, payload

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        if "choices" in response_data:
            return response_data["choices"][0]["message"]["content"].strip()
        elif "message" in response_data:
            return response_data["message"]["content"].strip()
        return response_data.get("content", "").strip()

    def _get_api_key(self) -> str:
        api_key = self.api_config.get("api_key", "")
        placeholder_keywords = ['你的', 'your', 'your_key', 'key']
        if not api_key or any(kw in api_key.lower() for kw in placeholder_keywords):
            env_key = os.environ.get(f"API_KEY_{self.name.upper().replace(' ', '_')}", "")
            if env_key:
                return env_key
        return api_key

    def validate_config(self) -> bool:
        api_key = self.api_config.get("api_key", "")
        if not api_key or any(kw in api_key.lower() for kw in ['你的', 'your', 'your_key']):
            env_key = os.environ.get(f"API_KEY_{self.name.upper().replace(' ', '_')}", "")
            if not env_key:
                return False
        return bool(self.api_config.get("api_url"))
