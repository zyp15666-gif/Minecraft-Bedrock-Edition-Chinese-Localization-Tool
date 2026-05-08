#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用例模块包
"""

from .adapt_entity_display_names import AdaptEntityDisplayNamesUseCase
from .batch_delete_value import BatchDeleteValueUseCase
from .batch_restore_value import BatchRestoreValueUseCase
from .extract_and_translate import ExtractAndTranslateUseCase
from .extract_only import ExtractOnlyUseCase
from .one_click_service import OneClickServiceUseCase
from .replace_display_names import ReplaceDisplayNamesUseCase
from .script_hardcode_translation import ScriptHardcodeTranslationUseCase
from .translate_lang_file import TranslateLangFileUseCase
from .translate_single_js_file import TranslateSingleJsFileUseCase

__all__ = [
    'ExtractOnlyUseCase',
    'ExtractAndTranslateUseCase',
    'ReplaceDisplayNamesUseCase',
    'OneClickServiceUseCase',
    'BatchDeleteValueUseCase',
    'BatchRestoreValueUseCase',
    'TranslateLangFileUseCase',
    'TranslateSingleJsFileUseCase',
    'AdaptEntityDisplayNamesUseCase',
    'ScriptHardcodeTranslationUseCase'
]
