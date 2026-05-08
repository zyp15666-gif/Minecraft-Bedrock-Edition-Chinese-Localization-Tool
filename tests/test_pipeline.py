#!/usr/bin/env python3
from unittest.mock import Mock, patch

import pytest

from core.pipeline import TranslationPipeline, create_pipeline, translate_lang_file_direct


class TestTranslationPipelineInit:
    def test_default_state(self):
        p = TranslationPipeline()
        assert p.config is None
        assert p.api_manager is None
        assert p.translator is None
        assert p.file_handler is None
        assert p.app_service is None
        assert p.initialized is False

    def test_config_path_stored(self):
        p = TranslationPipeline(config_path="/some/path")
        assert p.config_path == "/some/path"


class TestTranslationPipelineInitialize:
    @patch("core.pipeline.build_app_container")
    def test_successful_init(self, mock_build):
        mock_container = Mock()
        mock_container.config = {"test": True}
        mock_container.api_manager = Mock()
        mock_container.api_manager.detect_available_apis.return_value = [{"name": "api1"}]
        mock_container.translator = Mock()
        mock_container.file_handler = Mock()
        mock_container.app_service = Mock()
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        result = p.initialize()
        assert result is True
        assert p.initialized is True
        assert p.config == {"test": True}

    @patch("core.pipeline.build_app_container")
    def test_no_available_apis(self, mock_build):
        mock_container = Mock()
        mock_container.api_manager = Mock()
        mock_container.api_manager.detect_available_apis.return_value = []
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        result = p.initialize()
        assert result is False
        assert p.initialized is False

    @patch("core.pipeline.build_app_container")
    def test_exception_during_init(self, mock_build):
        mock_build.side_effect = Exception("config error")

        p = TranslationPipeline()
        result = p.initialize()
        assert result is False
        assert p.initialized is False


class TestGetComponents:
    def test_raises_when_not_initialized(self):
        p = TranslationPipeline()
        with pytest.raises(RuntimeError, match="未初始化"):
            p.get_components()

    @patch("core.pipeline.build_app_container")
    def test_returns_components_when_initialized(self, mock_build):
        mock_container = Mock()
        mock_container.config = {}
        mock_container.api_manager = Mock()
        mock_container.api_manager.detect_available_apis.return_value = [{"name": "api1"}]
        mock_container.translator = Mock()
        mock_container.file_handler = Mock()
        mock_container.app_service = Mock()
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        p.initialize()
        api_mgr, translator, fh, app_svc = p.get_components()
        assert api_mgr is mock_container.api_manager
        assert translator is mock_container.translator
        assert fh is mock_container.file_handler
        assert app_svc is mock_container.app_service


class TestTranslateLangFile:
    @patch("core.pipeline.build_app_container")
    def test_not_initialized_auto_init_fails(self, mock_build):
        mock_build.side_effect = Exception("fail")
        p = TranslationPipeline()
        result = p.translate_lang_file("/in", "/out")
        assert result is False

    @patch("core.pipeline.build_app_container")
    def test_input_file_not_exists(self, mock_build):
        mock_container = Mock()
        mock_container.config = {}
        mock_container.api_manager = Mock()
        mock_container.api_manager.detect_available_apis.return_value = [{"name": "api1"}]
        mock_container.translator = Mock()
        mock_container.file_handler = Mock()
        mock_container.app_service = Mock()
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        p.initialized = True
        p.api_manager = mock_container.api_manager
        p.translator = mock_container.translator
        p.file_handler = mock_container.file_handler

        with patch("os.path.exists", return_value=False):
            log_cb = Mock()
            result = p.translate_lang_file("/nonexistent", "/out", log_callback=log_cb)
        assert result is False

    @patch("core.pipeline.build_app_container")
    def test_no_entries(self, mock_build):
        mock_container = Mock()
        mock_container.config = {}
        mock_container.api_manager = Mock()
        mock_container.translator = Mock()
        mock_container.file_handler = Mock()
        mock_container.file_handler.parse_lang_file.return_value = {}
        mock_container.app_service = Mock()
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        p.initialized = True
        p.file_handler = mock_container.file_handler
        p.translator = mock_container.translator

        with patch("os.path.exists", return_value=True):
            log_cb = Mock()
            result = p.translate_lang_file("/in", "/out", log_callback=log_cb)
        assert result is False

    @patch("core.pipeline.build_app_container")
    def test_translation_failure(self, mock_build):
        mock_container = Mock()
        mock_container.config = {}
        mock_container.api_manager = Mock()
        mock_container.translator = Mock()
        mock_container.file_handler = Mock()
        mock_container.file_handler.parse_lang_file.return_value = {"key": "value"}
        mock_container.translator.translate_entries.return_value = None
        mock_container.app_service = Mock()
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        p.initialized = True
        p.file_handler = mock_container.file_handler
        p.translator = mock_container.translator

        with patch("os.path.exists", return_value=True):
            log_cb = Mock()
            result = p.translate_lang_file("/in", "/out", log_callback=log_cb)
        assert result is False

    @patch("core.pipeline.build_app_container")
    def test_exception_during_translation(self, mock_build):
        mock_container = Mock()
        mock_container.config = {}
        mock_container.api_manager = Mock()
        mock_container.translator = Mock()
        mock_container.file_handler = Mock()
        mock_container.file_handler.parse_lang_file.side_effect = RuntimeError("parse error")
        mock_container.app_service = Mock()
        mock_build.return_value = mock_container

        p = TranslationPipeline()
        p.initialized = True
        p.file_handler = mock_container.file_handler
        p.translator = mock_container.translator

        with patch("os.path.exists", return_value=True):
            log_cb = Mock()
            result = p.translate_lang_file("/in", "/out", log_callback=log_cb)
        assert result is False


class TestBatchTranslateFiles:
    def test_batch_translates_multiple_files(self):
        p = TranslationPipeline()
        p.initialized = True

        with patch.object(p, "translate_lang_file", return_value=True):
            results = p.batch_translate_files(
                [("/in1", "/out1"), ("/in2", "/out2")],
                log_callback=Mock()
            )
        assert results == {"/in1": True, "/in2": True}

    def test_batch_mixed_results(self):
        p = TranslationPipeline()
        p.initialized = True

        call_count = [0]

        def side_effect(inp, out, **kwargs):
            call_count[0] += 1
            return call_count[0] == 1

        with patch.object(p, "translate_lang_file", side_effect=side_effect):
            results = p.batch_translate_files(
                [("/in1", "/out1"), ("/in2", "/out2")],
                log_callback=Mock()
            )
        assert results["/in1"] is True
        assert results["/in2"] is False


class TestCreatePipeline:
    def test_creates_pipeline(self):
        p = create_pipeline(config_path="test.yml")
        assert isinstance(p, TranslationPipeline)
        assert p.config_path == "test.yml"


class TestTranslateLangFileDirect:
    @patch("core.pipeline.TranslationPipeline")
    def test_delegates_to_pipeline(self, mock_pipeline_cls):
        mock_instance = Mock()
        mock_instance.translate_lang_file.return_value = True
        mock_pipeline_cls.return_value = mock_instance

        result = translate_lang_file_direct("/in", "/out")
        assert result is True
        mock_instance.translate_lang_file.assert_called_once()
