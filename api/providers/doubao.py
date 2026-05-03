#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包 AI 提供商
"""

from .openai_compatible import OpenAICompatibleProvider


class DoubaoProvider(OpenAICompatibleProvider):
    """豆包 AI 提供商"""

    PROVIDER_TYPE = "doubao"
