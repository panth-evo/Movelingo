# System prompt shared across reading tasks
SYSTEM_PROMPT = """You are an expert {exam_name} ({cefr} level) exam writer.
You write highly realistic, original reading exam materials in the target language.
Do NOT copy or paraphrase official exam materials. All text must be newly written.
Every item must be answerable from the text alone.
You must return your response strictly as JSON that matches the required schema.
"""

def get_prompt(task_type: str, exam_name: str, cefr: str, language: str, topic: str, words_min: int, words_max: int, item_count: int, options_count: int = None) -> dict:
    """Returns a dict with 'system' and 'user' prompt strings."""
    
    system = SYSTEM_PROMPT.format(exam_name=exam_name, cefr=cefr)
    
    base_user = (
        f"Language: {language}\n"
        f"Level: {cefr}\n"
        f"Topic focus (with relocation angle): {topic}\n"
        f"Text length: Between {words_min} and {words_max} words.\n"
        f"Item count: {item_count} items.\n\n"
    )
    
    if task_type == "true_false_email":
        user = base_user + (
            "Task: Write an informal email from a friend about the topic. "
            "Then, create True/False questions based on the email. "
            "Return JSON with 'passage' (the email text) and 'items' (list of questions). "
            "Each item should have 'type': 'true_false', 'prompt': the statement, "
            "and 'options': [{'key': 'True', 'is_correct': true/false}, {'key': 'False', 'is_correct': true/false}]. "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "mcq_text":
        opts = f" {options_count} options per item." if options_count else ""
        user = base_user + (
            "Task: Write two short press texts or informative articles about the topic. "
            f"Then, create multiple choice questions based on the texts.{opts} "
            "Return JSON with 'passage' (list of the texts) and 'items' (list of questions). "
            "Each item should have 'type': 'mcq', 'prompt': the question, "
            "and 'options': list of option dicts with 'key' (e.g. A, B, C), 'text', and 'is_correct' boolean. "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "matching_ads":
        opts = f" {options_count} ads to match." if options_count else ""
        user = base_user + (
            f"Task: Write a list of {options_count or 10} short advertisements/notices (A, B, C...) related to the topic. "
            f"Then, write {item_count} short descriptions of people's situations. "
            "The user must match each situation to the correct ad. One situation might have no matching ad (option '0'). "
            "Return JSON with 'passage' (list of ads with their letter) and 'items' (the situations). "
            "Each item should have 'type': 'matching', 'prompt': the situation, "
            "and 'options': list of dicts with 'key' (the ad letter, or '0') and 'is_correct' boolean. "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "yes_no_opinions":
        user = base_user + (
            "Task: Write a short debate question, followed by several short forum comments from different people answering it. "
            f"Create {item_count} items asking whether a specific person is in favour or against the topic. "
            "Return JSON with 'passage' (the forum text) and 'items'. "
            "Each item should have 'type': 'yes_no', 'prompt': e.g., 'Does [Name] agree?', "
            "and 'options': [{'key': 'Yes', 'is_correct': true/false}, {'key': 'No', 'is_correct': true/false}]. "
            "Exactly one option per item must have is_correct = true."
        )
    elif task_type == "mcq_notice":
        opts = f" {options_count} options per item." if options_count else ""
        user = base_user + (
            "Task: Write a short formal notice, house rules, or instructions. "
            f"Then, create multiple choice questions based on it.{opts} "
            "Return JSON with 'passage' (the notice) and 'items'. "
            "Each item should have 'type': 'mcq', 'prompt': the question, "
            "and 'options': list of option dicts with 'key', 'text', and 'is_correct'. "
            "Exactly one option per item must have is_correct = true."
        )
    else:
        opts = f" {options_count} options per item." if options_count else ""
        user = base_user + (
            "Task: Write a text about the topic. "
            f"Then, create multiple choice questions based on the text.{opts} "
            "Return JSON with 'passage' and 'items'. "
            "Each item should have 'type': 'mcq', 'prompt': the question, "
            "and 'options': list of option dicts with 'key', 'text', and 'is_correct'. "
            "Exactly one option per item must have is_correct = true."
        )
        
    return {"system": system, "user": user}
