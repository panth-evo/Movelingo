import pytest
from engines.exams.spec_loader import load_all_specs, get_spec, summarize

def test_load_all_specs():
    specs = load_all_specs()
    assert "goethe_b1" in specs
    assert specs["goethe_b1"]["language"] == "de"

def test_get_spec():
    spec = get_spec("goethe_b1")
    assert spec["spec_id"] == "goethe_b1"

def test_summarize():
    spec = get_spec("goethe_b1")
    summary = summarize(spec)
    assert summary["spec_id"] == "goethe_b1"
    assert summary["language"] == "de"
    assert summary["exam_name"] == "Goethe-Zertifikat B1"
    assert len(summary["sections"]) == 4
    
    reading_summary = next(s for s in summary["sections"] if s["skill"] == "reading")
    assert reading_summary["duration_min"] == 65
    assert reading_summary["parts"] == 5
