#!/usr/bin/env python3
import json

import pytest

from api.terminology.exporter import TerminologyExporter
from api.terminology.loader import TerminologyLoader


@pytest.fixture
def loader(tmp_path):
    dict_path = tmp_path / "test_terms.json"
    dict_path.write_text('{"Chest": "箱子", "Turret": "炮塔"}', encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(TerminologyLoader, "_build_automaton", lambda self: None)
        mp.setattr(TerminologyLoader, "_load_spelling_corrections", lambda self: None)
        ldr = TerminologyLoader(config={"advanced": {"terminology": {"use_automaton": False}}})
        ldr.terms = {"Chest": "箱子", "Turret": "炮塔"}
        ldr.lower_terms = {k.lower(): v for k, v in ldr.terms.items()}
        ldr.clean_terms = dict(ldr.terms)
        ldr.clean_lower_terms = {k.lower(): v for k, v in ldr.clean_terms.items()}
        ldr.dict_path = str(dict_path)
        ldr.meta = {"version": "1.0"}
        return ldr


@pytest.fixture
def exporter(loader):
    return TerminologyExporter(loader)


class TestExportTerms:
    def test_export_json(self, exporter, loader, tmp_path):
        output = tmp_path / "export.json"
        result = exporter.export_terms(str(output), format="json")
        assert result is True
        data = json.loads(output.read_text(encoding="utf-8"))
        assert "Chest" in data
        assert data["Chest"] == "箱子"
        assert "_meta" in data

    def test_export_tsv(self, exporter, tmp_path):
        output = tmp_path / "export.tsv"
        result = exporter.export_terms(str(output), format="tsv")
        assert result is True
        content = output.read_text(encoding="utf-8")
        assert "Chest\t箱子" in content

    def test_export_unsupported_format(self, exporter, tmp_path):
        output = tmp_path / "export.csv"
        result = exporter.export_terms(str(output), format="csv")
        assert result is False

    def test_export_creates_directory(self, exporter, tmp_path):
        output = tmp_path / "subdir" / "export.json"
        result = exporter.export_terms(str(output), format="json")
        assert result is True
        assert output.exists()


class TestImportTerms:
    def test_import_json(self, exporter, loader, tmp_path):
        input_file = tmp_path / "import.json"
        input_file.write_text('{"Drone": "无人机", "Chest": "宝箱"}', encoding="utf-8")
        count = exporter.import_terms(str(input_file))
        assert count == 1
        assert loader.terms["Drone"] == "无人机"

    def test_import_json_overwrite(self, exporter, loader, tmp_path):
        input_file = tmp_path / "import.json"
        input_file.write_text('{"Chest": "宝箱"}', encoding="utf-8")
        count = exporter.import_terms(str(input_file), overwrite=True)
        assert count == 1
        assert loader.terms["Chest"] == "宝箱"

    def test_import_tsv(self, exporter, loader, tmp_path):
        input_file = tmp_path / "import.tsv"
        input_file.write_text("Drone\t无人机\n", encoding="utf-8")
        count = exporter.import_terms(str(input_file))
        assert count == 1
        assert loader.terms["Drone"] == "无人机"

    def test_import_replace(self, exporter, loader, tmp_path):
        input_file = tmp_path / "import.json"
        input_file.write_text('{"NewTerm": "新术语"}', encoding="utf-8")
        count = exporter.import_terms(str(input_file), replace=True)
        assert count == 1
        assert "Chest" not in loader.terms
        assert loader.terms["NewTerm"] == "新术语"

    def test_import_nonexistent_file(self, exporter):
        count = exporter.import_terms("/nonexistent/path.json")
        assert count == 0


class TestAddTermsBatch:
    def test_add_new_terms(self, exporter, loader):
        count = exporter.add_terms_batch({"Drone": "无人机", "Beacon": "信标"})
        assert count == 2
        assert loader.terms["Drone"] == "无人机"

    def test_add_existing_no_overwrite(self, exporter, loader):
        count = exporter.add_terms_batch({"Chest": "宝箱"})
        assert count == 0
        assert loader.terms["Chest"] == "箱子"

    def test_add_existing_with_overwrite(self, exporter, loader):
        count = exporter.add_terms_batch({"Chest": "宝箱"}, overwrite=True)
        assert count == 1
        assert loader.terms["Chest"] == "宝箱"


class TestMergeTermDicts:
    def test_merge_into_current(self, exporter, loader, tmp_path):
        source = tmp_path / "source.json"
        source.write_text('{"Drone": "无人机"}', encoding="utf-8")
        result = exporter.merge_term_dicts(str(source))
        assert "Drone" in result

    def test_merge_into_target(self, exporter, tmp_path):
        source = tmp_path / "source.json"
        source.write_text('{"Drone": "无人机"}', encoding="utf-8")
        target = tmp_path / "target.json"
        target.write_text('{"Chest": "箱子"}', encoding="utf-8")
        result = exporter.merge_term_dicts(str(source), str(target))
        assert "Drone" in result
        assert "Chest" in result

    def test_merge_nonexistent_target(self, exporter, tmp_path):
        source = tmp_path / "source.json"
        source.write_text('{"Drone": "无人机"}', encoding="utf-8")
        result = exporter.merge_term_dicts(str(source), str(tmp_path / "nonexistent.json"))
        assert "Drone" in result

    def test_merge_tsv_source(self, exporter, tmp_path):
        source = tmp_path / "source.tsv"
        source.write_text("Drone\t无人机\n", encoding="utf-8")
        result = exporter.merge_term_dicts(str(source))
        assert "Drone" in result

    def test_merge_with_overwrite(self, exporter, loader, tmp_path):
        source = tmp_path / "source.json"
        source.write_text('{"Chest": "宝箱"}', encoding="utf-8")
        result = exporter.merge_term_dicts(str(source), overwrite=True)
        assert result["Chest"] == "宝箱"
