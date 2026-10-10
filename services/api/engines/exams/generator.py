import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

from ai.llm_client import generate_json, LLMError
from ai.prompts.exams.reading import get_prompt as get_reading_prompt
from ai.prompts.exams.listening import get_prompt as get_listening_prompt
from engines.exams.validators import check_part
from ai.topics import get_random_topic

logger = logging.getLogger(__name__)

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "passage": { "type": ["string", "array"] },
        "audio": {
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "segment_id": { "type": "string" },
                            "script": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "speaker": { "type": "string" },
                                        "text": { "type": "string" },
                                        "voice_hint": { "type": "string" }
                                    },
                                    "required": ["speaker", "text", "voice_hint"]
                                }
                            }
                        },
                        "required": ["segment_id", "script"]
                    }
                }
            },
            "required": ["segments"]
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": { "type": "string" },
                    "prompt": { "type": "string" },
                    "segment_id": { "type": "string" },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": { "type": "string" },
                                "text": { "type": "string" },
                                "is_correct": { "type": "boolean" }
                            },
                            "required": ["key", "is_correct"]
                        }
                    }
                },
                "required": ["type", "prompt", "options"]
            }
        }
    },
    "anyOf": [
        {"required": ["passage", "items"]},
        {"required": ["audio", "items"]}
    ]
}

def generate_part(spec: dict, section: dict, part: dict, topic_seed: str, language: str, cefr: str) -> dict:
    mode = os.environ.get("LLM_MODE", "mock").lower()
    spec_id = spec.get("spec_id")
    part_no = part.get("part_no")
    task_type = part.get("task_type")
    skill = section.get("skill")
    
    if mode == "mock":
        generated = _build_mock_part(part, skill)
        if skill == "listening" and "audio" in generated:
            spec_audio = part.get("audio", {})
            generated["audio"]["preview_seconds"] = spec_audio.get("preview_seconds", 0)
            for seg in generated["audio"].get("segments", []):
                seg["play_limit"] = spec_audio.get("plays_per_segment", 1)
        return generated

    topic = get_random_topic(topic_seed)
    
    item_count = part.get("item_count", 0)
    options_count = part.get("options_count")
    
    if skill == "listening":
        segments_count = part.get("audio", {}).get("segments", 1)
        prompts = get_listening_prompt(
            task_type=task_type,
            exam_name=spec.get("exam_name", "Exam"),
            cefr=cefr,
            language=language,
            topic=topic,
            item_count=item_count,
            options_count=options_count,
            segments_count=segments_count
        )
    else:
        text_conf = part.get("text", {})
        words_min = text_conf.get("words_min", 100)
        words_max = text_conf.get("words_max", 200)
        prompts = get_reading_prompt(
            task_type=task_type,
            exam_name=spec.get("exam_name", "Exam"),
            cefr=cefr,
            language=language,
            topic=topic,
            words_min=words_min,
            words_max=words_max,
            item_count=item_count,
            options_count=options_count
        )
    
    system_prompt = prompts["system"]
    user_prompt = prompts["user"]
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            generated = generate_json(
                task=f"{spec_id}_part_{part_no}",
                system=system_prompt,
                user=user_prompt,
                schema=ITEM_SCHEMA,
                max_retries=1
            )
            
            if skill == "listening" and "audio" in generated:
                spec_audio = part.get("audio", {})
                generated["audio"]["preview_seconds"] = spec_audio.get("preview_seconds", 0)
                for seg in generated["audio"].get("segments", []):
                    seg["play_limit"] = spec_audio.get("plays_per_segment", 1)
            
            check_part(part, generated, language, cefr)
            
            # Cache the valid sample
            import json
            from pathlib import Path
            sample_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "exam_specs" / spec_id / "samples"
            sample_dir.mkdir(parents=True, exist_ok=True)
            sample_path = sample_dir / f"{skill}_part_{part['part_no']}.json"
            if not sample_path.exists():
                with open(sample_path, "w", encoding="utf-8") as f:
                    json.dump(generated, f, indent=2, ensure_ascii=False)
                    
            return generated
            
        except (ValueError, LLMError) as e:
            logger.warning(f"Validation failed on attempt {attempt+1} for part {part_no}: {str(e)}")
            user_prompt += f"\n\nYour previous response failed validation with this error: {str(e)}. Please correct it."
    
    logger.error(f"Failed to generate part {part_no} after {max_retries + 1} attempts. Falling back to cached sample.")
    return _get_cached_sample(spec_id, part_no)

def _build_mock_part(part: dict, skill: str) -> dict:
    item_count = part.get("item_count", 0)
    item_type = part.get("item_type", "mcq")
    options_count = part.get("options_count", 3)
    
    items = []
    
    if skill == "listening":
        segments_count = part.get("audio", {}).get("segments", 1)
        segments = []
        for s in range(segments_count):
            segments.append({
                "segment_id": f"seg_{s}",
                "script": [
                    {"speaker": "Speaker 1", "text": "Mock audio text.", "voice_hint": "male_1"}
                ]
            })
            
        for i in range(item_count):
            options = []
            for j in range(options_count or 2):
                options.append({
                    "key": chr(65 + j) if item_type != "true_false" else ("True" if j==0 else "False"),
                    "text": f"Option {j}",
                    "is_correct": j == 0
                })
            
            items.append({
                "type": item_type,
                "prompt": f"Mock question {i+1}?",
                "segment_id": f"seg_{i % segments_count}",
                "options": options
            })
            
        return {
            "audio": {"segments": segments},
            "items": items
        }
    else:
        passage_length = part.get("text", {}).get("words_min", 100)
        passage = " ".join(["mock_word"] * passage_length)
        
        for i in range(item_count):
            options = []
            for j in range(options_count or 2):
                options.append({
                    "key": chr(65 + j) if item_type != "true_false" else ("True" if j==0 else "False"),
                    "text": f"Option {j}",
                    "is_correct": j == 0
                })
            
            items.append({
                "type": item_type,
                "prompt": f"Mock question {i+1}?",
                "options": options
            })
            
        return {
            "passage": passage,
            "items": items
        }

def _get_cached_sample(spec_id: str, part_no: int) -> dict:
    sample_path = Path(__file__).resolve().parent.parent.parent / "data" / "exam_specs" / spec_id / "samples" / f"part_{part_no}.json"
    if sample_path.exists():
        with open(sample_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"_failed": True, "passage": "Failed to generate text and no sample found.", "items": []}
