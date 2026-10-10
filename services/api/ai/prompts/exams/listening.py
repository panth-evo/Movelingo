# System prompt shared across listening tasks
SYSTEM_PROMPT = """You are an expert {exam_name} ({cefr} level) exam writer.
You write highly realistic, original listening exam materials in the target language.
Do NOT copy or paraphrase official exam materials. All text must be newly written.
Write in natural spoken language (short sentences, a few fillers, not written-style prose).
The script must contain the information for every item, and no item may be answerable without listening.
You must return your response strictly as JSON that matches the required schema.
"""

def get_prompt(task_type: str, exam_name: str, cefr: str, language: str, topic: str, item_count: int, options_count: int = None, segments_count: int = 1) -> dict:
    system = SYSTEM_PROMPT.format(exam_name=exam_name, cefr=cefr)
    
    base_user = (
        f"Language: {language}\n"
        f"Level: {cefr}\n"
        f"Topic focus (with relocation angle): {topic}\n"
        f"Segments count: {segments_count} audio segments.\n"
        f"Item count: {item_count} items.\n\n"
        "Return JSON with 'audio' (containing 'segments') and 'items'.\n"
        "Each segment in 'segments' must have a 'segment_id' (e.g., 'seg_0', 'seg_1') and a 'script' array.\n"
        "Each script line must have 'speaker' (name or role), 'text' (what they say), and 'voice_hint' (e.g., 'male_1', 'female_1').\n"
        "Each item in 'items' must include 'segment_id' linking it to the correct audio segment where the answer is found.\n\n"
    )
    
    if task_type == "short_texts":
        opts = f" {options_count} options per item." if options_count else ""
        user = base_user + (
            f"Task: Write {segments_count} short unrelated texts (voicemail, radio announcement, station announcement). "
            f"Each text is a separate segment. Create 1 item per segment.{opts} "
            "Item type: 'mcq' or 'true_false' as specified by options (use 'mcq' with options array). "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "talk_or_announcement":
        opts = f" {options_count} options per item." if options_count else ""
        user = base_user + (
            "Task: Write a single extended talk, presentation, or public announcement (1 segment). "
            f"Create {item_count} multiple choice questions based on it.{opts} "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "conversation_two_speakers":
        opts = f" {options_count} options per item." if options_count else ""
        user = base_user + (
            "Task: Write a single conversation between exactly two speakers (1 segment). "
            f"Create {item_count} true/false or multiple choice questions based on it.{opts} "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "discussion_three_speakers":
        user = base_user + (
            "Task: Write a discussion between a host and two guests (3 speakers total, 1 segment). "
            f"Create {item_count} matching items where the user must identify which speaker expressed a specific opinion or statement. "
            "Item type: 'matching'. Options should be the speakers' names. "
            "Exactly one option per item must have is_correct = true."
        )
    else:
        user = base_user + (
            "Task: Write an audio script. "
            f"Create {item_count} questions based on it. "
            "Exactly one option per item must have is_correct = true."
        )
        
    return {"system": system, "user": user}
