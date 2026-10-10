def check_part(spec_part: dict, generated_part: dict) -> bool:
    """
    Raises ValueError if validation fails, otherwise returns True.
    """
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
        gen_segments = len(generated_part["audio"].get("segments", []))
        if gen_segments != spec_segments:
            raise ValueError(f"Expected {spec_segments} audio segments, got {gen_segments}")

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
