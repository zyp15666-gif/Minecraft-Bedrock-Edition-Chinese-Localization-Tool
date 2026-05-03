#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/utils.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.utils import (
    split_by_color_codes,
    has_color_codes,
    normalize_game_text,
    contains_color_codes,
    normalize_text_for_cache,
    sanitize_log_message,
    CallbackWrapper,
)


class TestSplitByColorCodes:
    def test_plain_text(self):
        result = split_by_color_codes("Hello World")
        assert len(result) == 1
        assert result[0] == ('', 'Hello World')

    def test_single_color_code(self):
        result = split_by_color_codes("§aHello")
        assert len(result) == 1
        assert result[0] == ('§a', 'Hello')

    def test_multiple_color_codes(self):
        result = split_by_color_codes("§aHello §rworld")
        assert len(result) == 2
        assert result[0] == ('§a', 'Hello ')
        assert result[1] == ('§r', 'world')

    def test_empty_text(self):
        result = split_by_color_codes("")
        assert len(result) == 1
        assert result[0] == ('', '')

    def test_color_code_at_end(self):
        result = split_by_color_codes("Hello§a")
        assert len(result) == 2
        assert result[0] == ('', 'Hello')
        assert result[1] == ('§a', '')


class TestHasColorCodes:
    def test_with_section_symbol(self):
        assert has_color_codes("§aHello") is True

    def test_with_hex_escape(self):
        assert has_color_codes("\\xA7aHello") is True

    def test_with_byte_escape(self):
        assert has_color_codes("\xA7aHello") is True

    def test_plain_text(self):
        assert has_color_codes("Hello World") is False

    def test_empty_text(self):
        assert has_color_codes("") is False

    def test_none_text(self):
        assert has_color_codes(None) is False


class TestNormalizeGameText:
    def test_plain_text(self):
        core, suffix = normalize_game_text("Hello World")
        assert core == "Hello World"
        assert suffix == ''

    def test_with_comment_suffix(self):
        core, suffix = normalize_game_text("Hello#comment")
        assert core == "Hello"
        assert suffix == "#comment"

    def test_with_newline_escape(self):
        core, suffix = normalize_game_text("Hello\\nWorld")
        assert "Hello" in core
        assert "World" in core

    def test_with_tab_escape(self):
        core, suffix = normalize_game_text("Hello\\tWorld")
        assert "Hello" in core
        assert "World" in core

    def test_extra_spaces(self):
        core, suffix = normalize_game_text("Hello    World")
        assert core == "Hello World"

    def test_leading_trailing_spaces(self):
        core, suffix = normalize_game_text("  Hello World  ")
        assert core == "Hello World"

    def test_empty_text(self):
        core, suffix = normalize_game_text("")
        assert core == ""
        assert suffix == ''

    def test_comment_with_spaces(self):
        core, suffix = normalize_game_text("  Hello  #  comment  ")
        assert core == "Hello"
        assert suffix == "#  comment  "


class TestContainsColorCodes:
    def test_with_color_code(self):
        assert contains_color_codes("§6Golden") is True

    def test_without_color_code(self):
        assert contains_color_codes("Golden") is False

    def test_empty_text(self):
        assert contains_color_codes("") is False


class TestNormalizeTextForCache:
    def test_strips_whitespace(self):
        assert normalize_text_for_cache("  Hello  ") == "Hello"

    def test_preserves_internal_spaces(self):
        assert normalize_text_for_cache("Hello  World") == "Hello  World"

    def test_empty_text(self):
        assert normalize_text_for_cache("") == ""


class TestSanitizeLogMessage:
    def test_hides_sk_key(self):
        result = sanitize_log_message("key=sk-abc123def456ghi789jkl012mno345")
        assert "sk-***REDACTED***" in result
        assert "abc123" not in result

    def test_hides_bearer_token(self):
        result = sanitize_log_message("Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234567890")
        assert "Bearer ***REDACTED***" in result

    def test_hides_api_key_param(self):
        result = sanitize_log_message('api_key="abcdefghijklmnopqrstuvwxyz123456"')
        assert "***REDACTED***" in result

    def test_preserves_normal_text(self):
        result = sanitize_log_message("翻译完成，共100条")
        assert result == "翻译完成，共100条"

    def test_empty_message(self):
        assert sanitize_log_message("") == ""


class TestCallbackWrapper:
    def test_log_callback(self):
        messages = []
        wrapper = CallbackWrapper(log_callback=lambda msg: messages.append(msg))
        wrapper.log("test message")
        assert messages == ["test message"]

    def test_progress_callback(self):
        progress_values = []
        wrapper = CallbackWrapper(
            progress_callback=lambda v, r, t: progress_values.append(v))
        wrapper.progress(0.5, 10, 5)
        assert progress_values == [0.5]

    def test_no_callbacks(self):
        wrapper = CallbackWrapper()
        wrapper.log("test")
        wrapper.progress(0.5)
