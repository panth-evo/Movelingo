import pytest
import sys
from fastapi import FastAPI
from fastapi.testclient import TestClient

from db import Base, engine
from routers.exams import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Ensure DB is created
Base.metadata.create_all(bind=engine)

def test_get_specs():
    response = client.get("/api/exams/specs?language=de")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    goethe_spec = next((s for s in data if s["spec_id"] == "goethe_b1"), None)
    assert goethe_spec is not None
    assert goethe_spec["language"] == "de"
    assert goethe_spec["exam_name"] == "Goethe-Zertifikat B1"

def test_generate_and_get_paper(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    
    payload = {
        "language": "de",
        "spec_id": "goethe_b1",
        "scope": "part",
        "skill": "reading",
        "part_no": 1
    }
    gen_res = client.post("/api/exams/generate", json=payload, headers={"x-user-id": "tester"})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "paper_id" in gen_data
    assert gen_data["status"] == "generating"
    
    paper_id = gen_data["paper_id"]
    
    get_res = client.get(f"/api/exams/papers/{paper_id}")
    assert get_res.status_code == 200
    paper_data = get_res.json()
    
    assert paper_data["paper_id"] == paper_id
    assert paper_data["status"] == "ready"
    assert paper_data["parts_ready"] == 1
    assert paper_data["parts_total"] == 1
    
    section = paper_data["sections"][0]
    part = section["parts"][0]
    assert "items" in part
    for item in part["items"]:
        for opt in item.get("options", []):
            assert "is_correct" not in opt

def test_generate_and_get_listening_paper(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    
    payload = {
        "language": "de",
        "spec_id": "goethe_b1",
        "scope": "section",
        "skill": "listening"
    }
    gen_res = client.post("/api/exams/generate", json=payload, headers={"x-user-id": "tester"})
    assert gen_res.status_code == 200
    paper_id = gen_res.json()["paper_id"]
    
    get_res = client.get(f"/api/exams/papers/{paper_id}")
    assert get_res.status_code == 200
    paper_data = get_res.json()
    
    section = next(s for s in paper_data["sections"] if s["skill"] == "listening")
    assert len(section["parts"]) == 4
    
    part1 = section["parts"][0]
    assert "audio" in part1
    assert "segments" in part1["audio"]
    assert "preview_seconds" in part1["audio"]
    
    seg_id = part1["audio"]["segments"][0]["segment_id"]
    audio_res = client.get(f"/api/exams/papers/{paper_id}/audio/{part1['part_no']}/{seg_id}")
    assert audio_res.status_code == 404
    
    monkeypatch.setenv("TTS_PROVIDER", "mock")
    audio_res_mock = client.get(f"/api/exams/papers/{paper_id}/audio/{part1['part_no']}/{seg_id}")
    assert audio_res_mock.status_code == 200
    assert audio_res_mock.headers["content-type"] == "audio/mpeg"
    assert audio_res_mock.content == b"MOCK_MP3_BYTES"

def test_submit_paper(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    
    payload = {
        "language": "de",
        "spec_id": "goethe_b1",
        "scope": "section",
        "skill": "reading"
    }
    gen_res = client.post("/api/exams/generate", json=payload, headers={"x-user-id": "tester"})
    paper_id = gen_res.json()["paper_id"]
    
    class MockProgressEngine:
        def __init__(self):
            self.called_with = None
        def record_progress_event(self, **kwargs):
            self.called_with = kwargs
        def compute_progress(self, user_id, language):
            return {"level": "B1", "percent": 50}
            
    mock_engine = MockProgressEngine()
    
    import types
    mock_module = types.ModuleType("engines.progress.progress_engine")
    mock_module.record_progress_event = mock_engine.record_progress_event
    mock_module.compute_progress = mock_engine.compute_progress
    sys.modules["engines.progress.progress_engine"] = mock_module
    
    submit_payload = {
        "skill": "reading",
        "answers": {
            "1": ["True", "False", "True", "False", "True", "False"],
            "2": ["a", "b", "c", "a", "b", "c"],
            "3": ["a", "b", "c", "d", "e", "f", "0"],
            "4": ["True", "False", "True", "False", "True", "False", "True"],
            "5": ["a", "b", "c", "a"]
        }
    }
    
    res = client.post(f"/api/exams/papers/{paper_id}/submit", json=submit_payload, headers={"x-user-id": "tester"})
    assert res.status_code == 200
    data = res.json()
    assert "score" in data
    assert "progress" in data
    assert data["progress"]["percent"] == 50
    
    assert mock_engine.called_with is not None
    assert mock_engine.called_with["user_id"] == "tester"
    assert mock_engine.called_with["skill"] == "reading"
    assert mock_engine.called_with["attempted"] == 30
    
    del sys.modules["engines.progress.progress_engine"]
