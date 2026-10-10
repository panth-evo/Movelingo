import json
from pathlib import Path

specs_dir = Path(__file__).resolve().parent.parent.parent / "data" / "exam_specs"

for path in specs_dir.rglob("*.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # fix root
    if "derived" not in data: data["derived"] = False
    if "pass_ratio" not in data: data["pass_ratio"] = 0.6
    if "scale_to" not in data: data["scale_to"] = 100
    
    # fix sections
    for section in data.get("sections", []):
        if "order_fixed" not in section: section["order_fixed"] = False
        
        # fix parts
        for part in section.get("parts", []):
            if "title" not in part: part["title"] = "Sample Title"
            
            if "speaking" in part:
                if "speaking_seconds" not in part["speaking"]:
                    part["speaking"]["speaking_seconds"] = 180
                    
            if "audio" in part:
                if "speakers" not in part["audio"]:
                    part["audio"]["speakers"] = 1
                if "kind" not in part["audio"]:
                    part["audio"]["kind"] = "dialogue"
                    
            if "criteria" in part:
                for crit in part["criteria"]:
                    if "max_points" in crit:
                        crit["max_points"] = int(round(crit["max_points"]))
                    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
print("Specs fixed.")
