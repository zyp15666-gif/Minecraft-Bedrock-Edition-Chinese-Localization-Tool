#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智谱 AI 提供商
"""

from typing import Dict, Any, Optional, Tuple
from .openai_compatible import OpenAICompatibleProvider


class ZhipuProvider(OpenAICompatibleProvider):
    """智谱 AI 提供商"""

    PROVIDER_TYPE = "zhipu"

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

        temperature = min(self.temperature, 1.0)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": temperature,
            "do_sample": True if temperature > 0 else False,
        }
        api_url = self.api_config["api_url"]
        return api_url, headers, payload
