#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 默认配置 - 所有 API 类型的 URL、模型、类型映射的唯一定义来源

UI 对话框、配置管理器、文档等均从此模块读取默认值，
避免分散硬编码导致不一致。
"""

API_URL_DEFAULTS = {
    "智谱": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "DeepSeek": "https://api.deepseek.com/v1/chat/completions",
    "通义千问": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "豆包": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    "本地 Ollama": "http://localhost:11434/api/chat",
    "OpenAI": "https://api.openai.com/v1/chat/completions",
    "Azure OpenAI": "https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT/chat/completions",
    "百度文心一言": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/",
    "讯飞星火": "https://spark-api.xf-yun.com/v1.1/chat",
    "Google Gemini": "https://generativelanguage.googleapis.com/v1beta/models/",
}

API_MODEL_PRESETS = {
    "智谱": ["glm-4-flash", "glm-4", "glm-4-plus", "glm-4-long"],
    "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
    "通义千问": ["qwen-turbo", "qwen-plus", "qwen-max"],
    "豆包": ["doubao-1.5-pro-32k", "doubao-1.5-lite-32k", "doubao-pro-32k"],
    "本地 Ollama": ["qwen2.5:7b", "llama3.1:8b", "gemma2:9b", "mistral:7b"],
    "OpenAI": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    "Azure OpenAI": ["gpt-4o-mini", "gpt-4o"],
    "百度文心一言": ["ernie-4.0-8k", "ernie-3.5-8k", "ernie-speed-8k"],
    "讯飞星火": ["generalv3.5", "generalv3", "lite"],
    "Google Gemini": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
}

API_TYPE_MAP = {
    "智谱": "zhipu",
    "DeepSeek": "deepseek",
    "通义千问": "qwen",
    "豆包": "doubao",
    "本地 Ollama": "local_ollama",
    "OpenAI": "openai",
    "Azure OpenAI": "azure_openai",
    "百度文心一言": "baidu_ernie",
    "讯飞星火": "iflytek_spark",
    "Google Gemini": "google_gemini",
}

API_TYPE_OPTIONS = list(API_URL_DEFAULTS.keys())

SUPPORTED_PROVIDER_KEYS = list(API_TYPE_MAP.values())
