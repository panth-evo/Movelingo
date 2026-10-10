import os
import json
import logging
from pathlib import Path
from engines.exams.grader import grade_subjective

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_calibration():
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    if not has_key:
        logger.warning("OPENAI_API_KEY not set. Calibration will run in mock mode.")
        os.environ["LLM_MODE"] = "mock"
    else:
        os.environ["LLM_MODE"] = "live"

    dataset_path = Path(__file__).resolve().parent.parent.parent / "data" / "evaluation" / "human_rated_samples.json"
    
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    band_values = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    
    total_samples = len(samples)
    total_criteria_scored = 0
    total_variance = 0
    
    print("\n--- GRADER CALIBRATION REPORT ---")
    print(f"{'Sample ID':<10} | {'Criterion':<22} | {'Human':<5} | {'AI':<5} | {'Variance'}")
    print("-" * 65)

    for sample in samples:
        sample_id = sample["sample_id"]
        language = sample["language"]
        cefr = sample["cefr"]
        skill = sample["skill"]
        task_prompt = sample["task_prompt"]
        user_text = sample["user_text"]
        human_scores = sample["human_scores"]

        spec_section = {
            "skill": skill,
            "parts": [
                {
                    "part_no": 1,
                    "criteria": [{"name": k, "max_points": 10} for k in human_scores.keys()]
                }
            ]
        }
        
        generated_section = {
            "parts": [
                {
                    "part_no": 1,
                    "task_type": skill,
                    "task_prompt": task_prompt
                }
            ]
        }
        
        user_texts = {"1": user_text}
        
        result = grade_subjective(spec_section, generated_section, user_texts, cefr, language, 0.6)
        
        part_result = result["per_part"].get("1", {})
        ai_criteria = {c["name"]: c["band"] for c in part_result.get("criteria", [])}
        
        for criterion_name, human_band in human_scores.items():
            ai_band = ai_criteria.get(criterion_name, "E")
            
            human_val = band_values.get(human_band, 1)
            ai_val = band_values.get(ai_band, 1)
            variance = ai_val - human_val
            
            total_variance += variance
            total_criteria_scored += 1
            
            var_str = f"{variance:+} bands"
            print(f"{sample_id:<10} | {criterion_name:<22} | {human_band:<5} | {ai_band:<5} | {var_str}")

    print("-" * 65)
    if total_criteria_scored > 0:
        avg_variance = total_variance / total_criteria_scored
        print(f"Average Variance: {avg_variance:+.2f} bands")
        if avg_variance < 0:
            print("Conclusion: The AI is grading slightly HARSHER than human examiners on average.")
        elif avg_variance > 0:
            print("Conclusion: The AI is grading slightly MORE LENIENTLY than human examiners on average.")
        else:
            print("Conclusion: The AI is perfectly calibrated with human examiners on average.")
    else:
        print("No criteria scored.")

if __name__ == "__main__":
    run_calibration()
