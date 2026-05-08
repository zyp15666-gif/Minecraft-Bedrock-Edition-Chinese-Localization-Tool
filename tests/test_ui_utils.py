#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 工具函数单元测试
"""

import time
from unittest.mock import MagicMock

import flet as ft
import pytest

from ui.utils import (
    ProgressThrottler,
    create_ui_scale,
    format_file_size,
    generate_api_name,
    get_theme_color,
    truncate_text,
)


class TestGetThemeColor:
    """get_theme_color 函数测试"""

    def test_light_mode(self):
        page = MagicMock()
        page.theme_mode = ft.ThemeMode.LIGHT

        theme_colors = {
            'light': {'bg': '#FFFFFF', 'text': '#000000'},
            'dark': {'bg': '#000000', 'text': '#FFFFFF'}
        }

        assert get_theme_color(page, theme_colors, 'bg') == '#FFFFFF'
        assert get_theme_color(page, theme_colors, 'text') == '#000000'

    def test_dark_mode(self):
        page = MagicMock()
        page.theme_mode = ft.ThemeMode.DARK

        theme_colors = {
            'light': {'bg': '#FFFFFF', 'text': '#000000'},
            'dark': {'bg': '#000000', 'text': '#FFFFFF'}
        }

        assert get_theme_color(page, theme_colors, 'bg') == '#000000'
        assert get_theme_color(page, theme_colors, 'text') == '#FFFFFF'

    def test_missing_color_returns_default(self):
        page = MagicMock()
        page.theme_mode = ft.ThemeMode.LIGHT

        theme_colors = {
            'light': {'bg': '#FFFFFF'},
            'dark': {'bg': '#000000'}
        }

        assert get_theme_color(page, theme_colors, 'missing') == ft.Colors.WHITE


class TestGenerateApiName:
    """generate_api_name 函数测试"""

    def test_empty_config(self):
        config = {}
        name = generate_api_name(config, "deepseek")
        assert name == "deepseek_1"

    def test_single_existing_api(self):
        config = {
            'deepseek': [{'name': 'deepseek_1'}]
        }
        name = generate_api_name(config, "deepseek")
        assert name == "deepseek_2"

    def test_multiple_existing_apis(self):
        config = {
            'deepseek': [
                {'name': 'deepseek_1'},
                {'name': 'deepseek_2'},
                {'name': 'deepseek_3'}
            ]
        }
        name = generate_api_name(config, "deepseek")
        assert name == "deepseek_4"

    def test_gap_in_numbers(self):
        config = {
            'deepseek': [
                {'name': 'deepseek_1'},
                {'name': 'deepseek_3'}
            ]
        }
        name = generate_api_name(config, "deepseek")
        assert name == "deepseek_2"

    def test_different_providers(self):
        config = {
            'deepseek': [{'name': 'deepseek_1'}],
            'zhipu': [{'name': 'zhipu_1'}]
        }
        name = generate_api_name(config, "zhipu")
        assert name == "zhipu_2"


class TestCreateUiScale:
    """create_ui_scale 函数测试"""

    def test_scale_1(self):
        scale = create_ui_scale(1.0)
        assert scale['title_size'] == 24
        assert scale['body_size'] == 14
        assert scale['padding'] == 15

    def test_scale_0_5(self):
        scale = create_ui_scale(0.5)
        assert scale['title_size'] == 12
        assert scale['body_size'] == 7
        assert scale['padding'] == 7

    def test_scale_2(self):
        scale = create_ui_scale(2.0)
        assert scale['title_size'] == 48
        assert scale['body_size'] == 28
        assert scale['padding'] == 30


class TestFormatFileSize:
    """format_file_size 函数测试"""

    def test_bytes(self):
        assert format_file_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"

    def test_megabytes(self):
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 5) == "5.00 MB"

    def test_gigabytes(self):
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_file_size(1024 * 1024 * 1024 * 2) == "2.00 GB"

    def test_zero(self):
        assert format_file_size(0) == "0 B"


class TestTruncateText:
    """truncate_text 函数测试"""

    def test_short_text(self):
        assert truncate_text("hello", 10) == "hello"

    def test_exact_length(self):
        assert truncate_text("hello", 5) == "hello"

    def test_long_text(self):
        result = truncate_text("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_custom_ellipsis(self):
        result = truncate_text("hello world", 8, ellipsis=">>>")
        assert result == "hello>>>"
        assert len(result) == 8

    def test_empty_text(self):
        assert truncate_text("", 10) == ""


class TestProgressThrottler:
    """ProgressThrottler 类测试"""

    def test_initial_state(self):
        throttler = ProgressThrottler()
        assert throttler.min_interval == 0.1
        assert throttler.significant_delta == 0.05

    def test_custom_params(self):
        throttler = ProgressThrottler(min_interval=0.5, significant_delta=0.1)
        assert throttler.min_interval == 0.5
        assert throttler.significant_delta == 0.1

    def test_first_update(self):
        throttler = ProgressThrottler(min_interval=0.1)
        assert throttler.should_update(0.0, "start") is True

    def test_significant_progress_change(self):
        throttler = ProgressThrottler(min_interval=10.0, significant_delta=0.05)

        throttler.should_update(0.0, "start")
        time.sleep(0.01)

        assert throttler.should_update(0.1, "progress") is True

    def test_insignificant_change_within_interval(self):
        throttler = ProgressThrottler(min_interval=10.0, significant_delta=0.05)

        throttler.should_update(0.0, "start")
        time.sleep(0.01)

        assert throttler.should_update(0.01, "progress") is False

    def test_time_elapsed(self):
        throttler = ProgressThrottler(min_interval=0.05)

        throttler.should_update(0.0, "start")
        time.sleep(0.1)

        assert throttler.should_update(0.01, "changed") is True

    def test_completion(self):
        throttler = ProgressThrottler(min_interval=10.0)

        throttler.should_update(0.5, "in progress")
        time.sleep(0.01)

        assert throttler.should_update(1.0, "done") is True

    def test_text_change_triggers(self):
        throttler = ProgressThrottler(min_interval=0.05, significant_delta=0.01)

        throttler.should_update(0.5, "original")
        time.sleep(0.1)

        assert throttler.should_update(0.5, "changed") is True

    def test_remaining_count_change_triggers(self):
        throttler = ProgressThrottler(min_interval=0.05, significant_delta=0.01)

        throttler.should_update(0.5, "text", remaining_count=10)
        time.sleep(0.1)

        assert throttler.should_update(0.5, "text", remaining_count=5) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
