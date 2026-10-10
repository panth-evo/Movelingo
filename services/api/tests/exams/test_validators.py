import pytest
from engines.exams.validators import check_part

def test_validators_accept_valid_part():
    spec_part = {
        "item_count": 2,
        "item_type": "mcq",
        "options_count": 3
    }
    gen_part = {
        "items": [
            {"type": "mcq", "options": [{"key": "a", "is_correct": True}, {"key": "b"}, {"key": "c"}]},
            {"type": "mcq", "options": [{"key": "a"}, {"key": "b", "is_correct": True}, {"key": "c"}]}
        ]
    }
    assert check_part(spec_part, gen_part) is True

def test_validators_reject_wrong_item_count():
    spec_part = {"item_count": 3, "item_type": "mcq"}
    gen_part = {"items": [{"type": "mcq"}]}
    with pytest.raises(ValueError, match="Expected 3 items"):
        check_part(spec_part, gen_part)

def test_validators_reject_two_correct_keys():
    spec_part = {"item_count": 1, "item_type": "mcq", "options_count": 3}
    gen_part = {
        "items": [
            {"type": "mcq", "options": [{"key": "a", "is_correct": True}, {"key": "b", "is_correct": True}, {"key": "c"}]}
        ]
    }
    with pytest.raises(ValueError, match="exactly 1 correct option"):
        check_part(spec_part, gen_part)
        
def test_validators_text_length():
    spec_part = {
        "item_count": 0,
        "text": {"words_min": 100, "words_max": 200}
    }
    
    # valid length (150 words)
    gen_part_valid = {"items": [], "passage": "word " * 150}
    assert check_part(spec_part, gen_part_valid) is True
    
    # 15% slack means min is 85, max is 230
    gen_part_short = {"items": [], "passage": "word " * 80}
    with pytest.raises(ValueError, match="out of bounds"):
        check_part(spec_part, gen_part_short)

def test_validators_audio_segments():
    spec_part = {
        "item_count": 0,
        "audio": {"segments": 2}
    }
    gen_part_valid = {"items": [], "audio": {"segments": [{}, {}]}}
    assert check_part(spec_part, gen_part_valid) is True
    
    gen_part_invalid = {"items": [], "audio": {"segments": [{}]}}
    with pytest.raises(ValueError, match="Expected 2 audio segments"):
        check_part(spec_part, gen_part_invalid)
