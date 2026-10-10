import pytest
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
