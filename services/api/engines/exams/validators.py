STOP_WORDS = {
    "de": {"der", "die", "das", "und", "ist", "in", "den", "von", "zu", "mit", "sich"},
    "es": {"el", "la", "los", "las", "y", "en", "es", "por", "para", "con", "un"},
    "fr": {"le", "la", "les", "et", "est", "en", "du", "au", "des", "un", "une"},
    "it": {"il", "la", "i", "le", "e", "in", "di", "a", "da", "un", "una"},
    "en": {"the", "and", "is", "in", "to", "of", "it", "that", "you", "for", "on"}
}

def check_language(text: str, language: str):
    if not text or language not in STOP_WORDS: return
    words = set(text.lower().split())
    target_stops = STOP_WORDS[language]
    en_stops = STOP_WORDS["en"]
    
    target_count = len(words.intersection(target_stops))
    en_count = len(words.intersection(en_stops))
    
    if en_count > target_count and language != "en":
        raise ValueError(f"Language guard failed: Expected {language}, but text appears to be English.")

import json
from pathlib import Path

_lexicon_cache = {}

def get_lexicon(language: str):
    if language not in _lexicon_cache:
        path = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge" / f"lexicon_{language}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _lexicon_cache[language] = json.load(f)
        else:
            _lexicon_cache[language] = {}
    return _lexicon_cache[language]

def check_vocabulary(text: str, language: str, cefr: str):
    lexicon = get_lexicon(language)
    if not lexicon:
        return
        
    cefr_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    if cefr.upper() not in cefr_levels:
        return
        
    target_idx = cefr_levels.index(cefr.upper())
    words = text.lower().replace(".", "").replace(",", "").replace("?", "").replace("!", "").split()
    
    out_of_level = 0
    for w in words:
        word_level_idx = -1
        for i, lvl in enumerate(cefr_levels):
            if lvl in lexicon and w in lexicon[lvl]:
                word_level_idx = i
                break
        
        if word_level_idx > target_idx:
            out_of_level += 1
            
    ratio = out_of_level / len(words) if words else 0
    if ratio > 0.1:
        raise ValueError(f"Vocabulary too advanced for {cefr}. {out_of_level} words exceed target level.")

def check_part(spec_part: dict, generated_part: dict, language: str = "de", cefr: str = "B1") -> bool:
    """
    Raises ValueError if validation fails, otherwise returns True.
    """
    if "passage" in generated_part:
        check_language(generated_part["passage"], language)
        check_vocabulary(generated_part["passage"], language, cefr)
    if "audio" in generated_part:
        for seg in generated_part["audio"].get("segments", []):
            for script_line in seg.get("script", []):
                text = script_line.get("text", "")
                check_language(text, language)
                check_vocabulary(text, language, cefr)
                
    # Check item count
    gen_items = generated_part.get("items", [])
    spec_item_count = spec_part.get("item_count", 0)
    
    if len(gen_items) != spec_item_count:
        raise ValueError(f"Expected {spec_item_count} items, got {len(gen_items)}")
        
    spec_item_type = spec_part.get("item_type")
    spec_options_count = spec_part.get("options_count")
    
    # Check items
    for i, item in enumerate(gen_items):
        if item.get("type") != spec_item_type:
            raise ValueError(f"Item {i} type mismatch: expected {spec_item_type}, got {item.get('type')}")
            
        options = item.get("options")
        if spec_options_count is not None and options is not None:
            if len(options) != spec_options_count:
                raise ValueError(f"Item {i} options count mismatch: expected {spec_options_count}, got {len(options)}")
        
        if options and spec_item_type in ["mcq", "true_false", "yes_no", "matching"]:
            correct_keys = [opt for opt in options if opt.get("is_correct") is True]
            if len(correct_keys) != 1:
                raise ValueError(f"Item {i} must have exactly 1 correct option, found {len(correct_keys)}")

    # Check text length
    if "text" in spec_part and "passage" in generated_part:
        if isinstance(generated_part["passage"], list):
            words = sum(len(str(p).split()) for p in generated_part["passage"])
        else:
            words = len(str(generated_part["passage"]).split())
            
        w_min = spec_part["text"]["words_min"]
        w_max = spec_part["text"]["words_max"]
        slack_min = int(w_min * 0.85)
        slack_max = int(w_max * 1.15)
        
        if not (slack_min <= words <= slack_max):
            raise ValueError(f"Text word count {words} out of bounds ({slack_min}-{slack_max})")

    # Check audio segments
    if "audio" in spec_part and "audio" in generated_part:
        spec_segments = spec_part["audio"]["segments"]
        segments = generated_part["audio"].get("segments", [])
        gen_segments = len(segments)
        if gen_segments != spec_segments:
            raise ValueError(f"Expected {spec_segments} audio segments, got {gen_segments}")
            
        valid_seg_ids = {s.get("segment_id") for s in segments if s.get("segment_id")}
        for i, item in enumerate(gen_items):
            if "segment_id" not in item:
                raise ValueError(f"Item {i} is missing segment_id")
            if item["segment_id"] not in valid_seg_ids:
                raise ValueError(f"Item {i} has invalid segment_id '{item.get('segment_id')}'")

    # Check writing tasks
    if "writing" in spec_part and "task" in generated_part:
        task = generated_part["task"]
        if task.get("kind") != "writing":
             raise ValueError("Generated task kind must be 'writing'")
        if not task.get("prompt"):
             raise ValueError("Writing task missing 'prompt'")

    # Check speaking tasks
    if "speaking" in spec_part and "task" in generated_part:
        task = generated_part["task"]
        if task.get("kind") != "speaking":
             raise ValueError("Generated task kind must be 'speaking'")
        if not task.get("prompt"):
             raise ValueError("Speaking task missing 'prompt'")

    return True
