"""Tests for the unified ingestion pipeline."""
from __future__ import annotations

import tempfile
from pathlib import Path

from construct.pipelines.ingestion import detect_source_type, ingest_source


def test_detect_file_type():
    tmp = tempfile.mkdtemp()
    test_file = Path(tmp) / "test.txt"
    test_file.write_text("test")
    assert detect_source_type(str(test_file)) == "file"


def test_detect_url_type():
    assert detect_source_type("https://example.com") == "url"
    assert detect_source_type("http://test.org/page") == "url"


def test_detect_note_type():
    assert detect_source_type("a quick thought") == "note"
    assert detect_source_type("") == "note"


def test_detect_research_type():
    assert detect_source_type("research:quantum gravity") == "research"


def test_ingest_note_no_workspace():
    result = ingest_source("/nonexistent/workspace", "test note")
    assert not result.success
