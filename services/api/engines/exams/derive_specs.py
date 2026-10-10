import json
import copy
import math
from pathlib import Path

SCALES = {
    "A1": 0.6,
    "A2": 0.8,
    "B2": 1.15,
    "C1": 1.3
}

def scale_value(val: int, multiplier: float) -> int:
    return max(1, round(val * multiplier))

def scale_duration(val: int, multiplier: float) -> int:
    scaled = round(val * multiplier)
    # round to nearest 5
    return max(5, 5 * round(scaled / 5))

def derive_specs():
    specs_dir = Path(__file__).resolve().parent.parent.parent / "data" / "exam_specs"
    
    b1_files = list(specs_dir.rglob("*_b1.json"))
    
    for b1_path in b1_files:
        with open(b1_path, "r", encoding="utf-8") as f:
            b1_spec = json.load(f)
            
        base_id = b1_spec["spec_id"].replace("_b1", "")
        lang = b1_spec["language"]
        lang_dir = b1_path.parent
        
        for cefr, multiplier in SCALES.items():
            derived = copy.deepcopy(b1_spec)
            derived["spec_id"] = f"{base_id}_{cefr.lower()}"
            derived["cefr"] = cefr
            derived["exam_name"] = derived["exam_name"].replace("B1", cefr)
            derived["derived"] = True
            
            for section in derived.get("sections", []):
                if "duration_min" in section:
                    section["duration_min"] = scale_duration(section["duration_min"], multiplier)
                
                for part in section.get("parts", []):
                    if "item_count" in part:
                        part["item_count"] = scale_value(part["item_count"], multiplier)
                        
                    if "text" in part:
                        if "words_min" in part["text"]:
                            part["text"]["words_min"] = scale_value(part["text"]["words_min"], multiplier)
                        if "words_max" in part["text"]:
                            part["text"]["words_max"] = scale_value(part["text"]["words_max"], multiplier)
                            
                    if "writing" in part:
                        if "min_words" in part["writing"]:
                            part["writing"]["min_words"] = scale_value(part["writing"]["min_words"], multiplier)
                        if "max_words" in part["writing"]:
                            part["writing"]["max_words"] = scale_value(part["writing"]["max_words"], multiplier)
                            
            out_path = lang_dir / f"{base_id}_{cefr.lower()}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(derived, f, indent=2, ensure_ascii=False)
                
    print(f"Derived {len(b1_files) * 4} specs successfully.")

if __name__ == "__main__":
    derive_specs()
