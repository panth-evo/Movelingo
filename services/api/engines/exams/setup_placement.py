import json
from pathlib import Path

langs = ["de", "es", "fr", "it"]
for lang in langs:
    spec = {
        "spec_id": f"placement_{lang}",
        "language": lang,
        "exam_name": "Placement Test",
        "cefr": "mixed",
        "derived": False,
        "pass_ratio": 0.6,
        "scale_to": 100,
        "sections": [
            {
                "skill": "placement",
                "duration_min": 20,
                "order_fixed": True,
                "parts": [
                    {
                        "part_no": 1,
                        "title": "Mixed objective items",
                        "task_type": "generic_mcq",
                        "item_type": "mcq",
                        "item_count": 20,
                        "items_data": [{"level": l} for l in ["A1"]*5 + ["A2"]*5 + ["B1"]*5 + ["B2"]*5]
                    }
                ]
            }
        ]
    }
    path = Path(__file__).resolve().parent.parent.parent / "data" / "exam_specs" / lang / f"placement_{lang}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)
print("Placement specs created.")
