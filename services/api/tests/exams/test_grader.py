import pytest
from engines.exams.grader import grade_objective, grade_subjective

def test_grade_objective_matching_zero():
    spec_section = {
        "parts": [
            {"part_no": 1, "items": [{}, {}]}
        ]
    }
    generated_section = {
        "parts": [
            {
                "part_no": 1, 
                "items": [
                    {"options": [{"key": "A", "is_correct": False}, {"key": "0", "is_correct": True}]},
                    {"options": [{"key": "B", "is_correct": True}]}
                ]
            }
        ]
    }
    user_answers = {"1": ["0", "B"]}
    
    result = grade_objective(spec_section, generated_section, user_answers, pass_ratio=0.5)
    assert result["raw"] == 2
    assert result["ratio"] == 1.0
    assert result["passed"] is True

def test_grade_objective_unanswered_scores_zero():
    spec_section = {"parts": [{"part_no": 1, "items": [{}, {}]}]}
    generated_section = {
        "parts": [
            {
                "part_no": 1, 
                "items": [
                    {"options": [{"key": "A", "is_correct": True}]},
                    {"options": [{"key": "B", "is_correct": True}]}
                ]
            }
        ]
    }
    user_answers = {"1": ["A"]}  # Missing second answer
    
    result = grade_objective(spec_section, generated_section, user_answers, pass_ratio=0.6)
    assert result["raw"] == 1
    assert result["ratio"] == 0.5
    assert result["passed"] is False

def test_grade_subjective_band_mapping(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    # Mock grader gives B to everything in mock mode (which is 75%)
    spec_section = {
        "skill": "writing",
        "parts": [
            {
                "part_no": 1,
                "writing": {"min_words": 10},
                "criteria": [{"name": "Task Fulfilment", "max_points": 20}]
            }
        ]
    }
    generated_section = {"parts": [{"part_no": 1, "task": "Write an email."}]}
    user_texts = {"1": "This is a valid text with enough words."}
    
    result = grade_subjective(spec_section, generated_section, user_texts, "B1", "de", 0.6)
    assert result["raw"] == 15  # 75% of 20
    assert result["ratio"] == 0.75
    assert result["ai_estimated"] is True

def test_grade_subjective_length_penalty():
    spec_section = {
        "skill": "writing",
        "parts": [
            {
                "part_no": 1,
                "writing": {"min_words": 100},
                "criteria": [{"name": "Task Fulfilment", "max_points": 20}]
            }
        ]
    }
    generated_section = {"parts": [{"part_no": 1}]}
    # < 50 words (50% of 100) -> auto E
    user_texts = {"1": "Too short"}
    
    result = grade_subjective(spec_section, generated_section, user_texts, "B1", "de", 0.6)
    assert result["raw"] == 0
    assert result["per_part"]["1"]["criteria"][0]["band"] == "E"

def test_grade_subjective_fulfilment_e_rule(monkeypatch):
    # If LLM gives E for fulfilment, score becomes 0
    monkeypatch.setenv("LLM_MODE", "live")
    
    def mock_generate_json(*args, **kwargs):
        return {
            "criteria": [
                {"name": "Task fulfilment", "band": "E", "feedback": ""},
                {"name": "Vocabulary", "band": "A", "feedback": ""}
            ],
            "summary": ""
        }
    
    monkeypatch.setattr("engines.exams.grader.generate_json", mock_generate_json)
    
    spec_section = {
        "skill": "writing",
        "parts": [
            {
                "part_no": 1,
                "writing": {"min_words": 10},
                "criteria": [
                    {"name": "Task fulfilment", "max_points": 20},
                    {"name": "Vocabulary", "max_points": 20}
                ]
            }
        ]
    }
    generated_section = {"parts": [{"part_no": 1}]}
    user_texts = {"1": "word " * 20}
    
    result = grade_subjective(spec_section, generated_section, user_texts, "B1", "de", 0.6)
    assert result["raw"] == 0  # Even though Vocabulary was A, fulfilment was E

def test_grade_subjective_wrong_criteria_rejection(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")
    
    call_count = 0
    def mock_generate_json(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First attempt: wrong criteria
            return {"criteria": [{"name": "Wrong Name", "band": "A", "feedback": ""}], "summary": ""}
        # Second attempt: right criteria
        return {"criteria": [{"name": "Task fulfilment", "band": "C", "feedback": ""}], "summary": ""}
        
    monkeypatch.setattr("engines.exams.grader.generate_json", mock_generate_json)
    
    spec_section = {
        "skill": "writing",
        "parts": [
            {
                "part_no": 1,
                "writing": {"min_words": 10},
                "criteria": [{"name": "Task fulfilment", "max_points": 20}]
            }
        ]
    }
    generated_section = {"parts": [{"part_no": 1}]}
    user_texts = {"1": "word " * 20}
    
    result = grade_subjective(spec_section, generated_section, user_texts, "B1", "de", 0.6)
    assert call_count == 2
    assert result["raw"] == 10  # C = 50% of 20
