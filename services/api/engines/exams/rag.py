import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_knowledge_path = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge" / "cefr_descriptors.json"
_cefr_cache = None

def _load_cefr_cache():
    global _cefr_cache
    if _cefr_cache is None:
        try:
            with open(_knowledge_path, "r", encoding="utf-8") as f:
                _cefr_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load CEFR descriptors: {e}")
            _cefr_cache = {}
    return _cefr_cache

def retrieve_cefr_rubrics(skill: str, cefr: str) -> str:
    """
    Retrieves the official CEFR descriptors for the given skill and level.
    Returns a formatted string that can be injected directly into the LLM prompt.
    """
    cache = _load_cefr_cache()
    level_data = cache.get(cefr.upper())
    if not level_data:
        return ""
        
    skill_data = level_data.get(skill.lower())
    if not skill_data:
        return ""
        
    rubric_str = f"--- OFFICIAL CEFR {cefr.upper()} DESCRIPTORS FOR {skill.upper()} ---\n"
    for criterion, descriptor in skill_data.items():
        rubric_str += f"* {criterion}: {descriptor}\n"
        
    return rubric_str
