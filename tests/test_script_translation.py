#!/usr/bin/env python3
import os
import tempfile
from unittest.mock import Mock, patch

from core.script_translation import (
    JSASTExtractor,
    ScriptTranslation,
    _build_string_literal,
    _try_translate,
    replace_strings_in_code,
    split_text_by_color_codes,
    translate_with_color_codes_v2,
)


class TestSplitTextByColorCodes:
    def test_plain_text(self):
        result = split_text_by_color_codes("hello world")
        assert result == [("", "hello world")]

    def test_single_color_code(self):
        result = split_text_by_color_codes("§aHello")
        assert len(result) == 1
        assert result[0][1] == "Hello"

    def test_multiple_color_codes(self):
        result = split_text_by_color_codes("§aHello §bWorld")
        assert len(result) == 2

    def test_empty_text(self):
        result = split_text_by_color_codes("")
        assert result == []

    def test_only_color_codes(self):
        result = split_text_by_color_codes("§a§b§c")
        assert len(result) >= 1

    def test_hex_color_code(self):
        result = split_text_by_color_codes("\\xA7aHello")
        assert len(result) >= 1


class TestTryTranslate:
    def test_empty_text(self):
        assert _try_translate("", Mock()) == ""

    def test_none_text(self):
        assert _try_translate(None, Mock()) is None

    def test_successful_translation(self):
        mock_api = Mock()
        mock_api.multi_api_translate.return_value = "翻译结果"
        result = _try_translate("hello", mock_api)
        assert result == "翻译结果"

    def test_translation_returns_none(self):
        mock_api = Mock()
        mock_api.multi_api_translate.return_value = None
        result = _try_translate("hello", mock_api)
        assert result == "hello"

    def test_translation_exception(self):
        mock_api = Mock()
        mock_api.multi_api_translate.side_effect = Exception("API error")
        result = _try_translate("hello", mock_api)
        assert result == "hello"

    def test_strips_color_codes_from_result(self):
        mock_api = Mock()
        mock_api.multi_api_translate.return_value = "§a翻译结果"
        result = _try_translate("hello", mock_api)
        assert "§" not in result
        assert result == "翻译结果"


class TestTranslateWithColorCodesV2:
    def test_no_color_codes(self):
        mock_api = Mock()
        mock_api.multi_api_translate.return_value = "翻译"
        with patch("core.utils.has_color_codes", return_value=False):
            result = translate_with_color_codes_v2("hello", mock_api)
        assert result == "翻译"

    def test_with_color_codes(self):
        mock_api = Mock()
        mock_api.multi_api_translate.return_value = "你好"
        with patch("core.utils.has_color_codes", return_value=True):
            with patch("core.script_translation.split_text_by_color_codes",
                       return_value=[("§a", "hello")]):
                result = translate_with_color_codes_v2("§ahello", mock_api)
        assert result is not None

    def test_empty_text(self):
        mock_api = Mock()
        with patch("core.utils.has_color_codes", return_value=False):
            result = translate_with_color_codes_v2("", mock_api)
        assert result == ""


class TestBuildStringLiteral:
    def test_double_quoted(self):
        result = _build_string_literal("hello", '"')
        assert result == '"hello"'

    def test_single_quoted(self):
        result = _build_string_literal("hello", "'")
        assert result == "'hello'"

    def test_template_literal(self):
        result = _build_string_literal("hello", '`')
        assert result == '`hello`'

    def test_escapes_double_quotes(self):
        result = _build_string_literal('he"llo', '"')
        assert '\\"' in result

    def test_escapes_single_quotes(self):
        result = _build_string_literal("he'llo", "'")
        assert "\\'" in result

    def test_escapes_backticks(self):
        result = _build_string_literal("he`llo", '`')
        assert '\\`' in result

    def test_escapes_newlines(self):
        result = _build_string_literal("he\nllo", '"')
        assert '\\n' in result

    def test_escapes_backslashes(self):
        result = _build_string_literal("he\\llo", '"')
        assert '\\\\' in result

    def test_template_with_placeholder(self):
        result = _build_string_literal("hello [[0]]", '`')
        assert '${0}' in result

    def test_strips_surrounding_quotes(self):
        result = _build_string_literal('"hello"', '"')
        assert result == '"hello"'

    def test_default_fallback(self):
        result = _build_string_literal("hello", "")
        assert result == '"hello"'


class TestJSASTExtractorShouldSkip:
    def test_empty_string(self):
        assert JSASTExtractor._should_skip("  ", "code", 0) is True

    def test_whitespace_only(self):
        assert JSASTExtractor._should_skip("\n\t", "code", 0) is True

    def test_path_prefix(self):
        assert JSASTExtractor._should_skip("textures/blocks/stone", "code", 0) is True

    def test_short_skip_word(self):
        assert JSASTExtractor._should_skip("ok", "code", 0) is True

    def test_digit_only(self):
        assert JSASTExtractor._should_skip("12345", "code", 0) is True

    def test_normal_text_not_skipped(self):
        assert JSASTExtractor._should_skip("Hello World", "code", 0) is False

    def test_color_code_only(self):
        assert JSASTExtractor._should_skip("§", "code", 0) is True

    def test_symbols_only(self):
        assert JSASTExtractor._should_skip("!@#$%", "code", 0) is True


class TestJSASTExtractorDetectContext:
    def test_property_key(self):
        code = '{ "key": "value" }'
        pos = code.index('"key"')
        result = JSASTExtractor._detect_context(code, pos)
        assert result == "property_key"

    def test_property_name(self):
        code = 'obj["prop"'
        pos = code.index('"prop"')
        result = JSASTExtractor._detect_context(code, pos)
        assert result == "property_name"

    def test_function_argument(self):
        code = 'func( "arg"'
        pos = code.index('"arg"')
        result = JSASTExtractor._detect_context(code, pos)
        assert result == "function_argument"

    def test_no_context(self):
        code = 'x = "hello"'
        pos = code.index('"hello"')
        result = JSASTExtractor._detect_context(code, pos)
        assert result == ""


class TestJSASTExtractorCache:
    def test_clear_cache(self):
        JSASTExtractor._strings_cache["test"] = [{"text": "hello"}]
        JSASTExtractor.clear_cache()
        assert len(JSASTExtractor._strings_cache) == 0

    def test_cache_store_and_retrieve(self):
        JSASTExtractor.clear_cache()
        strings = [{"text": "hello"}]
        JSASTExtractor._store_strings_in_cache("hash1", strings)
        assert "hash1" in JSASTExtractor._strings_cache

    def test_cache_eviction(self):
        JSASTExtractor.clear_cache()
        JSASTExtractor._strings_cache_maxsize = 2
        JSASTExtractor._store_strings_in_cache("h1", [{"text": "a"}])
        JSASTExtractor._store_strings_in_cache("h2", [{"text": "b"}])
        JSASTExtractor._store_strings_in_cache("h3", [{"text": "c"}])
        assert len(JSASTExtractor._strings_cache) == 2
        assert "h1" not in JSASTExtractor._strings_cache
        JSASTExtractor._strings_cache_maxsize = 100


class TestJSASTExtractorExtractStrings:
    def test_mode_1_filters_non_color(self):
        with patch.object(JSASTExtractor, '_extract_strings_internal', return_value=[
            {'text': 'hello', 'hasExpressions': False},
            {'text': '§aHello', 'hasExpressions': False},
        ]):
            result = JSASTExtractor.extract_strings("code", mode=1)
        assert len(result) == 1
        assert result[0]['text'] == '§aHello'

    def test_mode_2_returns_all(self):
        with patch.object(JSASTExtractor, '_extract_strings_internal', return_value=[
            {'text': 'hello', 'hasExpressions': False},
            {'text': '§aHello', 'hasExpressions': False},
        ]):
            result = JSASTExtractor.extract_strings("code", mode=2)
        assert len(result) == 2

    def test_filters_expressions(self):
        with patch.object(JSASTExtractor, '_extract_strings_internal', return_value=[
            {'text': 'hello', 'hasExpressions': True},
            {'text': 'world', 'hasExpressions': False},
        ]):
            result = JSASTExtractor.extract_strings("code", mode=2)
        assert len(result) == 1


class TestReplaceStringsInCode:
    def test_no_replacements(self):
        code = 'var x = "hello";'
        strings = [{'id': 's1', 'text': 'hello', 'range': (9, 16), 'quote': '"', 'context': ''}]
        trans_map = {}
        result = replace_strings_in_code(code, strings, trans_map)
        assert result == code

    def test_single_replacement(self):
        code = 'var x = "hello";'
        strings = [{'id': 's1', 'text': 'hello', 'range': (9, 16), 'quote': '"', 'context': ''}]
        trans_map = {'s1': {'translate': True, 'translation': '你好'}}
        result = replace_strings_in_code(code, strings, trans_map)
        assert '你好' in result
        assert 'hello' not in result

    def test_skip_unsafe_property_key(self):
        code = '{"name": "value"}'
        strings = [{'id': 's1', 'text': 'name', 'range': (2, 8), 'quote': '"', 'context': 'property_key'}]
        trans_map = {'s1': {'translate': True, 'translation': '名称'}}
        result = replace_strings_in_code(code, strings, trans_map)
        assert '名称' not in result

    def test_skip_translation_with_braces(self):
        code = 'var x = "hello";'
        strings = [{'id': 's1', 'text': 'hello', 'range': (9, 16), 'quote': '"', 'context': ''}]
        trans_map = {'s1': {'translate': True, 'translation': '{dangerous}'}}
        result = replace_strings_in_code(code, strings, trans_map)
        assert '{dangerous}' not in result


class TestScriptTranslationInit:
    def test_default_init(self):
        st = ScriptTranslation()
        assert st.translator is None
        assert st.api_manager is None

    def test_with_translator(self):
        mock_translator = Mock()
        mock_translator.api_manager = Mock()
        st = ScriptTranslation(mock_translator)
        assert st.api_manager is mock_translator.api_manager


class TestScriptTranslationScanJsFiles:
    def test_no_scripts_folder(self):
        st = ScriptTranslation()
        with tempfile.TemporaryDirectory() as tmp:
            result = st.scan_js_files(tmp)
        assert result == []

    def test_finds_js_files(self):
        st = ScriptTranslation()
        with tempfile.TemporaryDirectory() as tmp:
            scripts_dir = os.path.join(tmp, "scripts")
            os.makedirs(scripts_dir)
            with open(os.path.join(scripts_dir, "test.js"), "w", encoding="utf-8") as f:
                f.write('var x = "hello";')
            result = st.scan_js_files(tmp)
        assert len(result) == 1

    def test_ignores_non_js_files(self):
        st = ScriptTranslation()
        with tempfile.TemporaryDirectory() as tmp:
            scripts_dir = os.path.join(tmp, "scripts")
            os.makedirs(scripts_dir)
            with open(os.path.join(scripts_dir, "test.json"), "w") as f:
                f.write("{}")
            result = st.scan_js_files(tmp)
        assert result == []


class TestScriptTranslationTranslateJsFiles:
    def test_empty_file_list(self):
        st = ScriptTranslation()
        result = st.translate_js_files_with_ast([])
        assert result["success"] is True
        assert result["translated_files"] == []

    def test_with_mock_extraction(self):
        st = ScriptTranslation()
        mock_translator = Mock()
        mock_translator.api_manager = Mock()
        mock_translator.api_manager.get_available_apis.return_value = []
        mock_translator.api_manager.term_service = None
        st.translator = mock_translator

        with tempfile.TemporaryDirectory() as tmp:
            js_file = os.path.join(tmp, "test.js")
            with open(js_file, "w", encoding="utf-8") as f:
                f.write('var x = "§ahello";')

            with patch.object(JSASTExtractor, "extract_strings", return_value=[]):
                result = st.translate_js_files_with_ast([js_file])
        assert result["success"] is True
        assert js_file in result["unchanged_files"]


class TestScriptTranslationAnalyzePreview:
    def test_empty_file_list(self):
        st = ScriptTranslation()
        result = st.analyze_js_files_for_preview([])
        assert result["success"] is True
        assert result["file_analyses"] == []

    def test_analyze_with_mock(self):
        st = ScriptTranslation()
        with tempfile.TemporaryDirectory() as tmp:
            js_file = os.path.join(tmp, "test.js")
            with open(js_file, "w", encoding="utf-8") as f:
                f.write('var x = "hello";')

            with patch.object(JSASTExtractor, "extract_strings", return_value=[
                {'id': 's1', 'text': 'hello', 'hasExpressions': False}
            ]):
                result = st.analyze_js_files_for_preview([js_file])
        assert result["success"] is True
        assert len(result["file_analyses"]) == 1


class TestScriptTranslationHardcodeTranslation:
    def test_no_js_files(self):
        st = ScriptTranslation()
        with tempfile.TemporaryDirectory() as tmp:
            result = st.script_hardcode_translation(tmp)
        assert result["success"] is True
        assert "未找到" in result["message"]


class TestCreateScriptTranslation:
    def test_creates_instance(self):
        from core.script_translation import create_script_translation
        st = create_script_translation()
        assert isinstance(st, ScriptTranslation)

    def test_with_translator(self):
        from core.script_translation import create_script_translation
        mock_t = Mock()
        st = create_script_translation(mock_t)
        assert st.translator is mock_t
