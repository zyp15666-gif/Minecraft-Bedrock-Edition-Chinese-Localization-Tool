#!/usr/bin/env python3
from unittest.mock import Mock

import pytest

from api.batch_translation_coordinator import BatchTranslationCoordinator


class TestBatchTranslationCoordinatorInit:
    def test_default_config(self):
        coord = BatchTranslationCoordinator({})
        assert coord.enable_adaptive_batch is True
        assert coord.max_batch_size == 10
        assert coord.min_batch_size == 2

    def test_custom_config(self):
        config = {
            "advanced": {
                "translation": {
                    "enable_adaptive_batch": False,
                    "max_batch_size": 20,
                    "min_batch_size": 5,
                }
            }
        }
        coord = BatchTranslationCoordinator(config)
        assert coord.enable_adaptive_batch is False
        assert coord.max_batch_size == 20
        assert coord.min_batch_size == 5


class TestBatchTranslateFragments:
    @pytest.fixture
    def coord(self):
        return BatchTranslationCoordinator({})

    def test_empty_input(self, coord):
        result = coord.batch_translate_fragments(Mock(), {}, [])
        assert result == []

    def test_single_batch_success(self, coord):
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.return_value = "翻译A <<<SEP>>> 翻译B"

        result = coord.batch_translate_fragments(mock_client, api_config, ["textA", "textB"])
        assert len(result) == 2
        assert result[0] == "翻译A"
        assert result[1] == "翻译B"

    def test_translate_returns_none_falls_back(self, coord):
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.return_value = None

        result = coord.batch_translate_fragments(mock_client, api_config, ["textA", "textB"])
        assert result == ["textA", "textB"]

    def test_translate_raises_falls_back(self, coord):
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.side_effect = Exception("API error")

        result = coord.batch_translate_fragments(mock_client, api_config, ["textA", "textB"])
        assert result == ["textA", "textB"]

    def test_progress_callback(self, coord):
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.return_value = "翻译"
        progress_cb = Mock()
        log_cb = Mock()

        coord.batch_translate_fragments(
            mock_client, api_config, ["text1"],
            progress_callback=progress_cb, log_callback=log_cb
        )
        progress_cb.assert_called()
        log_cb.assert_called()

    def test_log_callback(self, coord):
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.return_value = "翻译"
        log_cb = Mock()

        coord.batch_translate_fragments(
            mock_client, api_config, ["text1"],
            log_callback=log_cb
        )
        log_cb.assert_called()


class TestAdaptiveBatchFragments:
    @pytest.fixture
    def coord(self):
        return BatchTranslationCoordinator({})

    def test_disabled_adaptive_uses_fixed(self):
        config = {"advanced": {"translation": {"enable_adaptive_batch": False}}}
        coord = BatchTranslationCoordinator(config)
        texts = ["a", "b", "c", "d", "e", "f", "a"]
        batches = coord._adaptive_batch_fragments(texts)
        assert len(batches) == 2
        assert len(batches[0]) == 5
        assert len(batches[1]) == 2

    def test_adaptive_splits_by_length(self, coord):
        long_text = "x" * 2500
        texts = [long_text, "short"]
        batches = coord._adaptive_batch_fragments(texts)
        assert len(batches) == 2

    def test_adaptive_respects_max_batch_size(self, coord):
        coord.max_batch_size = 3
        texts = ["a", "b", "c", "d", "e"]
        batches = coord._adaptive_batch_fragments(texts)
        for batch in batches:
            assert len(batch) <= 3

    def test_empty_input(self, coord):
        batches = coord._adaptive_batch_fragments([])
        assert batches == []

    def test_single_item(self, coord):
        batches = coord._adaptive_batch_fragments(["text"])
        assert len(batches) == 1
        assert batches[0] == ["text"]


class TestFixedBatch:
    @pytest.fixture
    def coord(self):
        return BatchTranslationCoordinator({})

    def test_exact_division(self, coord):
        result = coord._fixed_batch(["a", "b", "c", "d"], 2)
        assert result == [["a", "b"], ["c", "d"]]

    def test_remainder(self, coord):
        result = coord._fixed_batch(["a", "b", "c", "d", "e"], 2)
        assert result == [["a", "b"], ["c", "d"], ["e"]]

    def test_single_batch(self, coord):
        result = coord._fixed_batch(["a", "b"], 5)
        assert result == [["a", "b"]]

    def test_empty(self, coord):
        result = coord._fixed_batch([], 3)
        assert result == []


class TestRobustSplitTranslatedText:
    @pytest.fixture
    def coord(self):
        return BatchTranslationCoordinator({})

    def test_single_part(self, coord):
        result = coord._robust_split_translated_text("翻译", 1)
        assert result == ["翻译"]

    def test_exact_split(self, coord):
        text = "翻译A <<<SEP>>> 翻译B <<<SEP>>> 翻译C"
        result = coord._robust_split_translated_text(text, 3)
        assert len(result) == 3
        assert result[0] == "翻译A"
        assert result[1] == "翻译B"
        assert result[2] == "翻译C"

    def test_too_many_parts(self, coord):
        text = "A <<<SEP>>> B <<<SEP>>> C <<<SEP>>> D"
        result = coord._robust_split_translated_text(text, 2)
        assert len(result) == 2

    def test_too_few_parts(self, coord):
        text = "A <<<SEP>>> B"
        result = coord._robust_split_translated_text(text, 4)
        assert len(result) == 4
        assert result[2] == ""
        assert result[3] == ""


class TestBatchTranslateWithTerms:
    @pytest.fixture
    def coord(self):
        return BatchTranslationCoordinator({})

    def test_without_term_service(self, coord):
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.return_value = "翻译"

        result = coord.batch_translate_with_terms(mock_client, api_config, ["text"])
        assert len(result) == 1

    def test_with_term_service(self, coord):
        mock_term_service = Mock()
        mock_term_service.find_terms_in_text.return_value = []

        coord_with_terms = BatchTranslationCoordinator({}, term_service=mock_term_service)
        mock_client = Mock()
        api_config = {"name": "test"}
        mock_client.translate.return_value = "翻译"

        result = coord_with_terms.batch_translate_with_terms(mock_client, api_config, ["text"])
        assert len(result) == 1

    def test_empty_input(self, coord):
        result = coord.batch_translate_with_terms(Mock(), {}, [])
        assert result == []


class TestPreprocessWithTerms:
    def test_no_term_service(self):
        coord = BatchTranslationCoordinator({})
        text, replacements = coord._preprocess_with_terms("hello world")
        assert text == "hello world"
        assert replacements == {}

    def test_with_term_replacements(self):
        mock_term_service = Mock()
        mock_term_service.find_terms_in_text.return_value = [
            {"original": "Chest", "translation": "箱子"}
        ]
        coord = BatchTranslationCoordinator({}, term_service=mock_term_service)
        text, replacements = coord._preprocess_with_terms("Open the Chest")
        assert "Chest" not in text
        assert len(replacements) == 1


class TestPostprocessWithTerms:
    def test_replaces_placeholders(self):
        coord = BatchTranslationCoordinator({})
        replacements = {"__TERM_0__": "箱子", "__TERM_1__": "工作台"}
        result = coord._postprocess_with_terms("打开__TERM_0__使用__TERM_1__", replacements)
        assert result == "打开箱子使用工作台"

    def test_empty_replacements(self):
        coord = BatchTranslationCoordinator({})
        result = coord._postprocess_with_terms("hello", {})
        assert result == "hello"
