import math
import os
import logging
from typing import Dict, Any, List

from ai.llm_client import generate_json, LLMError

logger = logging.getLogger(__name__)

def grade_placement(spec_section: dict, generated_section: dict, user_answers: Dict[str, List[str]]) -> dict:
    level_stats = {"A1": {"raw": 0, "max": 0}, "A2": {"raw": 0, "max": 0}, "B1": {"raw": 0, "max": 0}, "B2": {"raw": 0, "max": 0}}
    parts_map = {str(p["part_no"]): p for p in generated_section.get("parts", [])}
    spec_parts_map = {str(p["part_no"]): p for p in spec_section.get("parts", [])}
    total_raw = 0
    total_max = 0
    
    for part_str, ans_list in user_answers.items():
        part = parts_map.get(part_str)
        spec_part = spec_parts_map.get(part_str)
        if not part or not spec_part:
            continue
            
        items_data = spec_part.get("items_data", [])
        items = part.get("items", [])
        for i, item in enumerate(items):
            level = items_data[i]["level"] if i < len(items_data) else "A1"
            if level not in level_stats:
                continue
            level_stats[level]["max"] += 1
            total_max += 1
            user_ans = ans_list[i] if i < len(ans_list) else None
            correct_opt = next((opt for opt in item.get("options", []) if opt.get("is_correct")), None)
            if correct_opt and user_ans and user_ans.strip().lower() == correct_opt["key"].strip().lower():
                level_stats[level]["raw"] += 1
                total_raw += 1
                
    placed_level = "A0"
    levels_in_order = ["A1", "A2", "B1", "B2"]
    for lvl in levels_in_order:
        stats = level_stats[lvl]
        if stats["max"] > 0 and (stats["raw"] / stats["max"]) >= 0.6:
            placed_level = lvl
        else:
            break
            
    return {
        "raw": total_raw,
        "max_points": total_max,
        "ratio": total_raw / total_max if total_max > 0 else 0,
        "scaled_100": round(100 * (total_raw / total_max)) if total_max > 0 else 0,
        "passed": placed_level != "A0",
        "placed_level": placed_level,
        "level_stats": level_stats,
        "pass_ratio": 0.6,
        "per_part": {}
    }

def grade_objective(spec_section: dict, generated_section: dict, user_answers: Dict[str, List[str]], pass_ratio: float, scale_to: int = 100) -> dict:
    """
    user_answers maps part_no (as string) to a list of answer keys.
    """
    total_raw = 0
    total_max = 0
    per_part = {}
    
    parts_map = {str(p["part_no"]): p for p in generated_section.get("parts", [])}
    spec_parts_map = {str(p["part_no"]): p for p in spec_section.get("parts", [])}
    
    for part_str, ans_list in user_answers.items():
        part = parts_map.get(part_str)
        spec_part = spec_parts_map.get(part_str)
        if not part or not spec_part:
            continue
            
        part_raw = 0
        items = part.get("items", [])
        part_max = len(items)
        
        for i, item in enumerate(items):
            user_ans = ans_list[i] if i < len(ans_list) else None
            
            correct_opt = next((opt for opt in item.get("options", []) if opt.get("is_correct")), None)
            
            if correct_opt and user_ans:
                if user_ans.strip().lower() == correct_opt["key"].strip().lower():
                    part_raw += 1
                    
        per_part[part_str] = {
            "raw": part_raw,
            "max": part_max,
            "ratio": part_raw / part_max if part_max > 0 else 0
        }
        total_raw += part_raw
        total_max += part_max
        
    ratio = total_raw / total_max if total_max > 0 else 0
    scaled_100 = round(scale_to * ratio)
    
    return {
        "raw": total_raw,
        "max_points": total_max,
        "ratio": ratio,
        "scaled_100": scaled_100,
        "passed": ratio >= pass_ratio,
        "pass_ratio": pass_ratio,
        "per_part": per_part
    }

def grade_subjective(spec_section: dict, generated_section: dict, user_texts: Dict[str, str], cefr: str, language: str, pass_ratio: float, scale_to: int = 100) -> dict:
    """
    user_texts maps part_no to the learner's written text or transcript.
    """
    total_raw = 0
    total_max = 0
    per_part = {}
    skill = spec_section.get("skill", "writing")
    
    parts_map = {str(p["part_no"]): p for p in generated_section.get("parts", [])}
    spec_parts_map = {str(p["part_no"]): p for p in spec_section.get("parts", [])}
    
    rubric_schema = {
        "type": "object",
        "properties": {
            "criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "band": {"type": "string", "enum": ["A", "B", "C", "D", "E"]},
                        "feedback": {"type": "string"}
                    },
                    "required": ["name", "band", "feedback"]
                }
            },
            "summary": {"type": "string"}
        },
        "required": ["criteria", "summary"]
    }
    
    for part_str, p_data in spec_parts_map.items():
        gen_part = parts_map.get(part_str, {})
        user_text = user_texts.get(part_str, "").strip()
        criteria = p_data.get("criteria", [])
        
        part_max = sum(c.get("max_points", 0) for c in criteria)
        total_max += part_max
        
        auto_e = False
        if skill == "writing":
            min_words = p_data.get("writing", {}).get("min_words", 0)
            word_count = len(user_text.split())
            if word_count < (min_words * 0.5):
                auto_e = True
        elif skill == "speaking":
            if not user_text:
                auto_e = True
                
        if auto_e:
            per_part[part_str] = {
                "raw": 0,
                "max": part_max,
                "ratio": 0,
                "summary": "Text under 50% of required length or empty transcript. Automatic E.",
                "criteria": [{"name": c["name"], "band": "E", "feedback": "Automatic E due to length.", "points": 0} for c in criteria]
            }
            continue
            
        mode = os.environ.get("LLM_MODE", "mock").lower()
        if mode == "mock":
            llm_result = {
                "criteria": [{"name": c["name"], "band": "B", "feedback": "Mock feedback"} for c in criteria],
                "summary": "Mock summary"
            }
        else:
            from engines.exams.rag import retrieve_cefr_rubrics
            rag_rubrics = retrieve_cefr_rubrics(skill, cefr)
            
            system_prompt = (
                f"You are a strict {cefr} level exam grader for {language}. Grade this {skill} task according to the criteria.\n\n"
                f"{rag_rubrics}\n"
                "You MUST base your grading entirely on these official descriptors. Explicitly cite them in your feedback to justify the band awarded."
            )
            
            task_type = gen_part.get("task_type", "")
            if task_type == "scenario_roleplay" and "scenario" in gen_part:
                context = gen_part["scenario"].get("context", "")
                persona = gen_part["scenario"].get("persona", "")
                goals = gen_part["scenario"].get("goals", [])
                goals_str = "\n".join([f"- {g}" for g in goals])
                user_prompt = (
                    f"Task is a Scenario Roleplay.\nContext: {context}\nAI Persona: {persona}\nGoals the learner needed to achieve:\n{goals_str}\n\n"
                    f"Learner Transcript:\n{user_text}\n\n"
                    "Criteria to grade (A is best, E is worst). Base 'Task fulfilment' strictly on how many goals were naturally achieved:\n"
                )
            else:
                user_prompt = f"Task:\n{gen_part}\n\nLearner Text:\n{user_text}\n\nCriteria to grade (A is best, E is worst):\n"
                
            for c in criteria:
                user_prompt += f"- {c['name']} (max {c['max_points']})\n"
                
            max_retries = 2
            llm_result = None
            for attempt in range(max_retries + 1):
                try:
                    result = generate_json(task=f"grade_{part_str}", system=system_prompt, user=user_prompt, schema=rubric_schema, max_retries=1)
                    
                    spec_names = {c["name"].lower() for c in criteria}
                    res_names = {c["name"].lower() for c in result.get("criteria", [])}
                    if spec_names != res_names:
                        raise ValueError(f"Criteria names mismatch. Expected {spec_names}, got {res_names}")
                        
                    llm_result = result
                    break
                except (ValueError, LLMError) as e:
                    logger.warning(f"Grading validation failed: {e}")
                    user_prompt += f"\n\nValidation failed: {str(e)}. Fix the criteria names."
                    
            if not llm_result:
                llm_result = {
                    "criteria": [{"name": c["name"], "band": "E", "feedback": "LLM Failure"} for c in criteria],
                    "summary": "LLM failed to grade properly."
                }
                
        part_raw = 0
        band_multipliers = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "E": 0.0}
        
        task_fulfilment_e = False
        scored_criteria = []
        for c in llm_result.get("criteria", []):
            spec_c = next((sc for sc in criteria if sc["name"].lower() == c["name"].lower()), None)
            if not spec_c:
                continue
                
            band = c["band"]
            c_max = spec_c["max_points"]
            pts = round(c_max * band_multipliers.get(band, 0.0))
            
            if "fulfilment" in c["name"].lower() and band == "E":
                task_fulfilment_e = True
                
            feedback_str = c["feedback"]
            if skill == "speaking" and "pronunciation" in c["name"].lower():
                feedback_str += " (Note: STT-based pronunciation judgement is only indicative.)"
                
            scored_criteria.append({
                "name": c["name"],
                "band": band,
                "feedback": feedback_str,
                "points": pts
            })
            part_raw += pts
            
        if task_fulfilment_e:
            part_raw = 0
            
        per_part[part_str] = {
            "raw": part_raw,
            "max": part_max,
            "ratio": part_raw / part_max if part_max > 0 else 0,
            "summary": llm_result.get("summary", ""),
            "criteria": scored_criteria
        }
        total_raw += part_raw
        
    ratio = total_raw / total_max if total_max > 0 else 0
    scaled_100 = round(scale_to * ratio)
    
    return {
        "raw": total_raw,
        "max_points": total_max,
        "ratio": ratio,
        "scaled_100": scaled_100,
        "passed": ratio >= pass_ratio,
        "pass_ratio": pass_ratio,
        "per_part": per_part,
        "ai_estimated": True
    }
