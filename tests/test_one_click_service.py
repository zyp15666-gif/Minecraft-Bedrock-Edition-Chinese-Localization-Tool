#!/usr/bin/env python3
from unittest.mock import Mock, patch

import pytest

from core.use_cases.one_click_service import OneClickServiceUseCase


@pytest.fixture
def mock_file_handler():
    fh = Mock()
    fh.extract_entries.return_value = {"key1": "value1", "key2": "value2"}
    fh.replace_display_names_with_lang_key.return_value = 3
    fh.merge_and_write_lang.return_value = None
    fh.ensure_languages_json.return_value = None
    fh.apply_hardcoded_translations.return_value = None
    fh.remove_value_from_json_folder.return_value = None
    return fh


@pytest.fixture
def mock_translator():
    t = Mock()
    t.translate_entries_batch.return_value = {"key1": "翻译1", "key2": "翻译2"}
    return t


@pytest.fixture
def use_case(mock_file_handler, mock_translator):
    return OneClickServiceUseCase(mock_file_handler, mock_translator)


class TestOneClickServiceUseCaseInit:
    def test_stores_dependencies(self, mock_file_handler, mock_translator):
        uc = OneClickServiceUseCase(mock_file_handler, mock_translator)
        assert uc.file_handler is mock_file_handler
        assert uc.translator is mock_translator


class TestOneClickServiceExecute:
    def test_no_bp_path(self, use_case):
        result = use_case.execute(bp_path="")
        assert result["success"] is False
        assert "BP" in result["message"]

    def test_no_entries_found(self, use_case, mock_file_handler):
        mock_file_handler.extract_entries.return_value = {}
        result = use_case.execute(bp_path="/some/path")
        assert result["success"] is True
        assert result["translate_count"] == 0

    def test_successful_execution(self, use_case):
        result = use_case.execute(bp_path="/some/bp")
        assert result["success"] is True
        assert result["replace_count"] == 3
        assert result["translate_count"] == 2

    def test_with_rp_path(self, use_case):
        with patch("os.path.exists", return_value=True):
            result = use_case.execute(bp_path="/some/bp", rp_path="/some/rp")
        assert result["success"] is True
        assert use_case.file_handler.merge_and_write_lang.call_count == 2

    def test_translation_failure(self, use_case, mock_translator):
        mock_translator.translate_entries_batch.return_value = None
        result = use_case.execute(bp_path="/some/bp")
        assert result["success"] is False
        assert result["translate_count"] == 0

    def test_exception_handling(self, use_case, mock_file_handler):
        mock_file_handler.extract_entries.side_effect = RuntimeError("disk error")
        result = use_case.execute(bp_path="/some/bp")
        assert result["success"] is False
        assert "disk error" in result["message"]

    def test_progress_callback(self, use_case):
        progress_cb = Mock()
        result = use_case.execute(bp_path="/some/bp", progress_callback=progress_cb)
        assert result["success"] is True
        progress_cb.assert_called()

    def test_log_callback(self, use_case):
        log_cb = Mock()
        result = use_case.execute(bp_path="/some/bp", log_callback=log_cb)
        assert result["success"] is True
        log_cb.assert_called()

    def test_hardcoded_translations_applied(self, use_case, mock_translator):
        mock_translator.translate_entries_batch.return_value = {
            "key1": "翻译1",
            "book.test": "书本翻译",
            "auto.test": "自动翻译",
        }
        result = use_case.execute(bp_path="/some/bp")
        assert result["success"] is True
        use_case.file_handler.apply_hardcoded_translations.assert_called()

    def test_no_hardcoded_entries(self, use_case):
        result = use_case.execute(bp_path="/some/bp")
        assert result["success"] is True
        use_case.file_handler.apply_hardcoded_translations.assert_not_called()

    def test_blocks_folder_cleanup(self, use_case):
        with patch("os.path.exists", return_value=True):
            with patch("os.path.join", return_value="/some/bp/blocks"):
                result = use_case.execute(bp_path="/some/bp")
        assert result["success"] is True

    def test_translate_progress_mapping(self, use_case, mock_translator):
        progress_cb = Mock()

        def fake_translate(entries, progress_fn, log_fn):
            if progress_fn:
                progress_fn(0.5, 5, 3)
            return {"key1": "翻译1", "key2": "翻译2"}

        mock_translator.translate_entries_batch.side_effect = fake_translate
        result = use_case.execute(bp_path="/some/bp", progress_callback=progress_cb)
        assert result["success"] is True
