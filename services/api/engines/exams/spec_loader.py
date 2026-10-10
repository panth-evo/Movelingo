import json
from pathlib import Path
from jsonschema import validate
from typing import Dict, List, Any

# Resolve path to data directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exam_specs"
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "ai" / "schemas" / "exam_spec.schema.json"

_schema_cache = None
_specs_cache = {}

def _get_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache

def load_all_specs() -> Dict[str, dict]:
    global _specs_cache
    if _specs_cache:
        return _specs_cache
        
    schema = _get_schema()
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir() or lang_dir.name.startswith("."):
            continue
            
        for spec_file in lang_dir.glob("*.json"):
            if spec_file.name == "SPEC_FORMAT.json":
                continue
            
            with open(spec_file, "r", encoding="utf-8") as f:
                spec = json.load(f)
                
            validate(instance=spec, schema=schema)
            _specs_cache[spec["spec_id"]] = spec
            
    return _specs_cache

def get_spec(spec_id: str) -> dict:
    specs = load_all_specs()
    if spec_id not in specs:
        raise ValueError(f"Spec not found: {spec_id}")
    return specs[spec_id]

def summarize(spec: dict) -> dict:
    sections_summary = []
    for section in spec.get("sections", []):
        sections_summary.append({
            "skill": section["skill"],
            "duration_min": section["duration_min"],
            "parts": len(section.get("parts", []))
        })
        
    return {
        "spec_id": spec["spec_id"],
        "exam_name": spec["exam_name"],
        "language": spec["language"],
        "cefr": spec["cefr"],
        "derived": spec.get("derived", False),
        "verified_on": spec.get("verified_on"),
        "sections": sections_summary
    }
