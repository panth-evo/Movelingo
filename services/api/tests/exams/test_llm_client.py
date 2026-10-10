import pytest
from pathlib import Path

from ai.llm_client import generate_json, chat_text, LLMError

def test_mock_mode_default_response(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    schema = {"type": "object"}
    
    res = generate_json(task="unknown_task", system="sys", user="user", schema=schema)
    assert res == {"_mock": True}

def test_mock_mode_file_response(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_MODE", "mock")
    
    import ai.llm_client
    mock_dir = Path(ai.llm_client.__file__).parent / "mock"
    mock_dir.mkdir(parents=True, exist_ok=True)
    
    task_name = "test_task"
    mock_file = mock_dir / f"{task_name}.json"
    mock_file.write_text('{"foo": "bar"}')
    
    try:
        schema = {"type": "object"}
        res = generate_json(task=task_name, system="sys", user="user", schema=schema)
        assert res == {"foo": "bar"}
    finally:
        mock_file.unlink()

def test_chat_text_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    res = chat_text(system="sys", user="user")
    assert res == "Canned reply for mock mode."
