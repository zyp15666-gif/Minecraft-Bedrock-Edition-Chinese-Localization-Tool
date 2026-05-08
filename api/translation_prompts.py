# translation_prompts.py
# 翻译提示词配置文件 - 支持按Provider类型获取专用提示词
# 两级结构: stages(翻译阶段) 和 providers(提供商专用)
#
# provider映射规则:
#   local_ollama       -> providers.local_ollama
#   openai_compatible  -> providers.openai_compatible
#   openai             -> providers.openai_compatible
#   azure_openai       -> providers.azure_openai
#   zhipu              -> providers.zhipu
#   doubao             -> providers.doubao
#
# 兼容旧格式: default.stage1, default.stage2 仍然可用

import os
from typing import Dict, Optional

import yaml

_PROMPTS_CACHE: Optional[Dict] = None

_LOCAL_OLLAMA_FALLBACK = (
    "将以下文本翻译为适合Minecraft的简体中文。必须严格遵守：\n"
    "1. 只输出译文，禁止添加任何解释、定义、拼音或额外符号。\n"
    "2. 原文中的换行符(\\n)和占位符（%1、%s、%d）必须原样保留。\n"
    "3. 原文中的反引号(`)必须原样保留，不要添加或删除反引号。\n"
    "4. 同一英文短语在全文中必须翻译一致。\n"
    "5. 翻译风格应简洁自然，符合Minecraft官方中文语言习惯。\n"
    "6. 若文本为语言键（含冒号和下划线），直接原样返回。\n"
    "7. 若文本为空或无法理解，直接原样返回。\n"
    "\n"
    "待翻译文本：\n"
)

_ZHIPU_FALLBACK = (
    "将以下英文文本翻译为适合Minecraft的简体中文。严格遵守：\n"
    "1. 只输出译文，禁止任何解释、注释、拼音或额外符号。\n"
    "2. 原文中的换行符(\\n)、制表符(\\t)和占位符（%1、%s、%d）必须原样保留。\n"
    "3. 同一英文短语在全文中的翻译必须保持一致。\n"
    "4. 翻译风格简洁自然，符合Minecraft官方简体中文语言习惯。\n"
    "5. 若文本为语言键（含冒号和下划线，如 item.stone.name），直接原样返回。\n"
    "\n待翻译文本：\n"
)

_STAGE1_FALLBACK = """你是一位专业的 Minecraft 游戏MOD汉化专家，精通简体中文译名和游戏内语言风格。
请将以下英文文本翻译为地道的中文，要求：

**直接翻译：**

1. **仅输出译文**，不添加任何解释、注释、拼音或额外内容。
2. **严格保留所有特殊符号**，包括但不限于：
   - 游戏内占位符（如 %s、%d、%1$s、%2$s、%1 等）必须保持原格式
   - 方括号 []、花括号 {}、圆括号 () 等所有标点符号
   - 反引号 ` 必须原样保留，不要添加或删除反引号
3. **如果文本是语言键（例如包含冒号和下划线的标识符，如 item.sgs_farm:garlic_crop），请勿翻译，直接原样返回。**
4. **如果文本看起来像是编码、变量名、函数名或技术标识符**（如 entity.ra_se:camera.name），不要尝试翻译，直接返回原文。
5. **保持游戏内自然的语气**，句子通顺，符合中文表达习惯。
6. **遇到 Minecraft 官方术语时，请尽量参照 Minecraft 简体中文译名**。
7. **特别注意**：不要修改任何看起来像游戏内部标识符的文本。

现在开始翻译："""

_STAGE2_FALLBACK = """你是一位专业的 Minecraft 游戏MOD汉化专家，精通简体中文译名和游戏内语言风格。
请将以下英文文本翻译为地道的中文，要求：

1. **仅输出译文**，不添加任何注释、解释或额外内容。
2. **严格处理以下特殊格式**：
   - **占位符**：如 %s、%d、%1$s、%2$s 等必须原样保留
   - **分隔符**：如 " <<<SEP>>> " 是文本片段分隔符，翻译时保持分隔符不变
   - **反引号**：反引号 ` 必须原样保留，不要添加或删除反引号
3. **如果文本是语言键（例如包含冒号和下划线的标识符，如 item.sgs_farm:garlic_crop），请勿翻译，直接原样返回。**
4. **注意处理以下情况**：
   - **分割的空白信息**：保持原有的空格和分隔
   - **英文符号**：如逗号、句号、冒号等应转换为中文对应符号
   - **无意义的字母组合**：如单独的两个字母（如 "a Drone" 中的 "a"）应合理翻译
   - **可能的占位符变体**：如 [TERM_0]、[术语_0] 等可能是术语占位符，应原样保留
5. **保持游戏内自然的语气**，句子通顺，符合中文表达习惯。
6. **遇到专业术语时，请尽量参照 Minecraft 官方简体中文译名**。
7. **特别注意**：如果文本被 " <<<SEP>>> " 分隔，这是多个独立文本片段，请分别翻译每个片段。

现在开始翻译："""


def _load_prompts_from_yaml() -> Optional[Dict]:
    """从 YAML 文件加载提示词，支持两级结构

    Returns:
        Dict包含:
            - stages: 翻译阶段提示词
            - providers: 提供商专用提示词
            - raw: 原始YAML数据
    """
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE

    yaml_path = os.path.join(
        os.path.dirname(__file__), '..', 'resources', 'prompts', 'translation_prompts.yml')
    if not os.path.exists(yaml_path):
        _PROMPTS_CACHE = {}
        return None

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        _PROMPTS_CACHE = {
            'stages': data.get('stages', {}),
            'providers': data.get('providers', {}),
            'raw': data
        }
        return _PROMPTS_CACHE
    except Exception:
        _PROMPTS_CACHE = {}
        return None


def get_prompt_for_provider(provider_type: str, stage: str = "stage1") -> str:
    """获取指定Provider类型的提示词（支持两级结构）

    Args:
        provider_type: Provider类型 (local_ollama, openai_compatible, zhipu, doubao等)
        stage: 翻译阶段 (stage1, stage2)

    Returns:
        提示词字符串
    """
    prompts = _load_prompts_from_yaml()
    if not prompts:
        return _get_fallback_prompt(provider_type, stage)

    providers = prompts.get('providers', {})

    if provider_type in providers:
        provider_config = providers[provider_type]
        if isinstance(provider_config, dict) and '__same_as__' in provider_config:
            target = provider_config['__same_as__']
            if target in providers:
                return providers[target]
        return provider_config

    stages = prompts.get('stages', {})
    if stage in stages:
        return stages[stage]

    return _get_fallback_prompt(provider_type, stage)


def get_stage_prompt(stage: str = "stage1") -> str:
    """获取指定翻译阶段的提示词

    Args:
        stage: 阶段名称 (stage1, stage2)

    Returns:
        阶段提示词
    """
    prompts = _load_prompts_from_yaml()
    if prompts:
        stages = prompts.get('stages', {})
        if stage in stages:
            return stages[stage]

    return _get_fallback_prompt("default", stage)


def _get_fallback_prompt(provider_type: str, stage: str) -> str:
    """获取回退提示词（当YAML加载失败时）"""
    fallbacks = {
        ("local_ollama", "stage1"): _LOCAL_OLLAMA_FALLBACK,
        ("local_ollama", "stage2"): _LOCAL_OLLAMA_FALLBACK,
        ("zhipu", "stage1"): _ZHIPU_FALLBACK,
        ("zhipu", "stage2"): _ZHIPU_FALLBACK,
        ("default", "stage1"): _STAGE1_FALLBACK,
        ("default", "stage2"): _STAGE2_FALLBACK,
    }
    return fallbacks.get((provider_type, stage), _STAGE1_FALLBACK)


def get_provider_types() -> list:
    """获取所有已配置的Provider类型"""
    prompts = _load_prompts_from_yaml()
    if prompts:
        return list(prompts.get('providers', {}).keys())
    return ["local_ollama", "openai_compatible", "zhipu", "doubao"]


def get_prompt(key: str, fallback: str = None) -> str:
    """获取提示词（兼容旧API）

    优先从YAML加载，支持新旧两种格式:
    - 新格式: stages.stage1, providers.local_ollama
    - 旧格式: default.stage1, local_model, hunyuan
    """
    external = _load_prompts_from_yaml()
    if not external:
        return fallback or ""

    if key in external.get('stages', {}):
        return external['stages'][key]

    if key in external.get('providers', {}):
        return external['providers'][key]

    return fallback or ""


def get_stage1_prompt() -> str:
    """阶段1提示词"""
    return _STAGE1_FALLBACK


def get_stage2_prompt() -> str:
    """阶段2提示词"""
    return _STAGE2_FALLBACK


def get_js_ast_judge_prompt() -> str:
    """JavaScript AST判断专用提示词"""
    external = _load_prompts_from_yaml()
    if external and 'js_ast_judge' in external.get('raw', {}):
        return external['raw']['js_ast_judge']
    return JS_AST_JUDGE_PROMPT


# ==================== JS AST 智能判断提示词 ====================

JS_AST_JUDGE_PROMPT = """你是一个 Minecraft 基岩版插件本地化专家。
下面是从 JavaScript 代码中提取的所有字符串字面量。
请逐条判断哪些需要翻译为简体中文。

**翻译优先级（必须遵守）：**

✅ **必须翻译的情况：**
1. **包含 § 符号的字符串** - 这是 Minecraft 颜色/格式代码，一定是玩家可见的UI文本，必须翻译
2. **包含空格+标点符号的完整句子** - 如 "Wild Seeds drop chance:"、"Enter keyword"、"Search!" 等UI文本
3. **UI方法的参数值** - 如 form.title("X")、form.textField("Y", "Z")、form.submitButton("W") 中的 "X"、"Y"、"Z"、"W"
4. **包含冒号(:)、问号(?)、感叹号(!)的文本** - 这些是完整的UI提示文本

❌ **绝对不要翻译的情况：**
1. **context 为 "property_key"** - 对象属性的键名，如 { "form": ... } 中的 "form"
2. **context 为 "property_name"** - 成员表达式的属性名，如 obj.prop 中的 "prop"
3. **资源路径** - 以 textures/、sounds/、models/ 等开头
4. **命令原文** - 以 / 开头
5. **命名空间标识符** - 如 sgs_farm:main、minecraft:stone
6. **全大写+下划线** - 如 SEED_CHANCE、REGIONAL_SEEDS（这是变量名）
7. **纯字母数字下划线组合** - 如 "wood"、"stone"、"copper"（技术标识符）
8. **版本号、纯数字、纯符号**

**翻译要求：**
- 保留所有 § 颜色代码
- 保留所有占位符（%s、%d、${...} 等）
- 保留换行符（\\n）
- 翻译符合 Minecraft 中文语言风格

输入格式（JSON 数组）：
[
  { "id": 0, "text": "§6Pet Furniture Guide Book", "context": "function_argument" },
  { "id": 1, "text": "form", "context": "property_key" },
  { "id": 2, "text": "Main Menu", "context": "function_argument" },
  { "id": 3, "text": "title", "context": "property_name" },
  { "id": 4, "text": "Search!", "context": "function_argument" },
  { "id": 5, "text": "Enter keyword", "context": "function_argument" }
]

输出格式（JSON 数组）：
[
  { "id": 0, "translate": true, "translation": "§6宠物家具指南书" },
  { "id": 1, "translate": false, "translation": null },
  { "id": 2, "translate": true, "translation": "主菜单" },
  { "id": 3, "translate": false, "translation": null },
  { "id": 4, "translate": true, "translation": "搜索！" },
  { "id": 5, "translate": true, "translation": "输入关键词" }
]

**关键提醒：**
- context 为 "function_argument" 时，这通常是 UI 方法的参数值（如 form.title("X") 中的 "X"），这些是需要翻译的UI文本！
- 只有当 text 本身是技术标识符（全大写、下划线、命名空间等）时才跳过，不要因为 context 是 "function_argument" 就跳过翻译！
- 当 context 为 "property_key"、"property_name" 或 "function_name" 时，必须返回 "translate": false！

注意：只输出 JSON，不要输出其他内容。"""
