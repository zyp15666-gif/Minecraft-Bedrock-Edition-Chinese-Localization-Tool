#!/usr/bin/env python3
from unittest.mock import Mock, patch

import pytest

from api.terminology.loader import TerminologyLoader
from api.terminology.matcher import TerminologyMatcher


@pytest.fixture
def loader():
    with patch.object(TerminologyLoader, '_build_automaton'):
        with patch.object(TerminologyLoader, '_load_spelling_corrections'):
            ldr = TerminologyLoader(config={"advanced": {"terminology": {"use_automaton": False}}})
            ldr.terms = {
                "Chest": "箱子",
                "Crafting Table": "工作台",
                "Turret": "炮塔",
                "Drone": "无人机",
            }
            ldr.lower_terms = {k.lower(): v for k, v in ldr.terms.items()}
            ldr.clean_terms = dict(ldr.terms)
            ldr.clean_lower_terms = {k.lower(): v for k, v in ldr.clean_terms.items()}
            ldr.spelling_mistakes = {"ereramic": "ceramic"}
            return ldr


@pytest.fixture
def matcher(loader):
    return TerminologyMatcher(loader)


class TestTerminologyMatcherInit:
    def test_init(self, loader):
        m = TerminologyMatcher(loader)
        assert m.loader is loader
        assert m.placeholder_prefix == "[["
        assert m.placeholder_suffix == "]]"


class TestPreprocess:
    def test_empty_text(self, matcher):
        text, mapping = matcher.preprocess("")
        assert text == ""
        assert mapping == {}

    def test_no_terms_found(self, matcher):
        text, mapping = matcher.preprocess("hello world")
        assert text == "hello world"
        assert mapping == {}

    def test_single_term_replaced(self, matcher):
        text, mapping = matcher.preprocess("Open the Chest")
        assert "Chest" not in text
        assert "[[TERM_0]]" in text
        assert "[[TERM_0]]" in mapping
        assert mapping["[[TERM_0]]"] == "箱子"

    def test_multiple_terms_replaced(self, matcher):
        text, mapping = matcher.preprocess("Use the Crafting Table near the Chest")
        assert len(mapping) == 2
        assert "Crafting Table" not in text
        assert "Chest" not in text

    def test_caching(self, matcher):
        result1 = matcher.preprocess("Open the Chest")
        result2 = matcher.preprocess("Open the Chest")
        assert result1 == result2

    def test_cache_lru_eviction(self, matcher):
        matcher._cache_max_size = 2
        matcher._preprocess_cache.clear()

        matcher.preprocess("text1 Chest")
        matcher.preprocess("text2 Turret")
        assert len(matcher._preprocess_cache) == 2

        matcher.preprocess("text3 Drone")
        assert len(matcher._preprocess_cache) == 2


class TestPostprocess:
    def test_empty_text(self, matcher):
        result = matcher.postprocess("")
        assert result == ""

    def test_with_placeholder_map(self, matcher):
        placeholder_map = {"[[TERM_0]]": "箱子", "[[TERM_1]]": "工作台"}
        text = "打开[[TERM_0]]使用[[TERM_1]]"
        result = matcher.postprocess(text, placeholder_map)
        assert result == "打开箱子使用工作台"

    def test_single_bracket_placeholder(self, matcher):
        placeholder_map = {"[[TERM_0]]": "箱子"}
        text = "打开[TERM_0]查看"
        result = matcher.postprocess(text, placeholder_map)
        assert "箱子" in result

    def test_double_bracket_placeholder(self, matcher):
        placeholder_map = {"[[TERM_0]]": "箱子"}
        text = "打开[[TERM_0]]查看"
        result = matcher.postprocess(text, placeholder_map)
        assert "箱子" in result

    def test_none_placeholder_map(self, matcher):
        result = matcher.postprocess("hello world", None)
        assert result == "hello world"

    def test_remaining_placeholder_cleanup(self, matcher):
        text = "some text [TERM_99] more"
        result = matcher.postprocess(text, {})
        assert "[TERM_99]" not in result


class TestGetTranslation:
    def test_exact_match(self, matcher):
        result = matcher.get_translation("Chest")
        assert result == "箱子"

    def test_case_insensitive_match(self, matcher):
        result = matcher.get_translation("chest")
        assert result == "箱子"

    def test_no_match(self, matcher):
        result = matcher.get_translation("nonexistent")
        assert result is None

    def test_empty_text(self, matcher):
        result = matcher.get_translation("")
        assert result is None


class TestGetTranslationOriginal:
    def test_exact_match(self, matcher):
        assert matcher.get_translation_original("Chest") == "箱子"

    def test_normalized_match(self, matcher):
        assert matcher.get_translation_original("Chest\r\n") == "箱子"

    def test_case_insensitive(self, matcher):
        assert matcher.get_translation_original("chest") == "箱子"

    def test_no_match(self, matcher):
        assert matcher.get_translation_original("unknown") is None

    def test_empty(self, matcher):
        assert matcher.get_translation_original("") is None


class TestGetTranslationClean:
    def test_exact_clean_match(self, matcher):
        assert matcher.get_translation_clean("Chest") == "箱子"

    def test_case_insensitive(self, matcher):
        assert matcher.get_translation_clean("chest") == "箱子"

    def test_no_match(self, matcher):
        assert matcher.get_translation_clean("unknown") is None

    def test_empty(self, matcher):
        assert matcher.get_translation_clean("") is None


class TestHasAnyTerm:
    def test_contains_term(self, matcher):
        assert matcher.has_any_term("Open the Chest") is True

    def test_no_term(self, matcher):
        matcher.loader.use_automaton = True
        matcher.loader.automaton = None
        assert matcher.has_any_term("hello world") is True

    def test_no_term_with_automaton(self, matcher):
        matcher.loader.use_automaton = True
        mock_automaton = Mock()
        mock_automaton.iter.return_value = iter([])
        matcher.loader.automaton = mock_automaton
        assert matcher.has_any_term("hello world") is False

    def test_empty_text(self, matcher):
        matcher.loader.use_automaton = False
        assert matcher.has_any_term("") is True


class TestFixSpelling:
    def test_fixes_known_mistake(self, matcher):
        result = matcher.fix_spelling("ereramic dish")
        assert result == "ceramic dish"

    def test_no_mistakes(self, matcher):
        result = matcher.fix_spelling("normal text")
        assert result == "normal text"
