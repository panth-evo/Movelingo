import os
import time
import asyncio
from db import SessionLocal
from engines.exams.assembler import create_paper_stub, generate_paper_async

def run_smoke():
    specs = {
        "de": "goethe_b1",
        "es": "dele_b1",
        "fr": "delf_b1",
        "it": "cils_b1",
        "de_place": "placement_de",
        "es_place": "placement_es",
        "fr_place": "placement_fr",
        "it_place": "placement_it"
    }
    
    print(f"{'Spec':<20} | {'Parts':<5} | {'Items':<5} | {'Valid':<5} | {'Seconds':<7}")
    print("-" * 55)
    
    for lang, spec_id in specs.items():
        os.environ["LLM_MODE"] = "mock"
        start_time = time.time()
        
        # 1. Full paper stub (scope="full") because smoke table expects all parts
        paper = create_paper_stub(spec_id, "full", "smoke_user")
        paper_id = paper.paper_id
        
        asyncio.run(generate_paper_async(paper_id, spec_id, lang, "B1", "full"))
        
        db = SessionLocal()
        from models.exams import ExamPaperModel
        completed_paper = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
        internal_json = completed_paper.internal_json
        db.close()
        
        elapsed = round(time.time() - start_time, 2)
        
        parts_count = 0
        items_count = 0
        valid = "Yes"
        for section in internal_json.get("sections", []):
            for part in section.get("parts", []):
                parts_count += 1
                items = part.get("items", [])
                items_count += len(items)
                if "_failed" in part:
                    valid = "No"
                    
        print(f"{spec_id:<20} | {parts_count:<5} | {items_count:<5} | {valid:<5} | {elapsed:<7.2f}")
        
        if os.environ.get("OPENAI_API_KEY"):
            os.environ["LLM_MODE"] = "live"
            start_time = time.time()
            
            paper_live = create_paper_stub(spec_id, "part", "smoke_user")
            paper_id_live = paper_live.paper_id
            
            asyncio.run(generate_paper_async(paper_id_live, spec_id, lang, "B1", "part", skill="reading", part_no=1))
            
            db = SessionLocal()
            completed_paper_live = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id_live).first()
            internal_json_live = completed_paper_live.internal_json
            db.close()
            
            elapsed_live = round(time.time() - start_time, 2)
            
            parts_count_live = 0
            items_count_live = 0
            valid_live = "Yes"
            for section in internal_json_live.get("sections", []):
                for part in section.get("parts", []):
                    parts_count_live += 1
                    items = part.get("items", [])
                    items_count_live += len(items)
                    if "_failed" in part:
                        valid_live = "No"
                        
            print(f"{spec_id+' (live)':<20} | {parts_count_live:<5} | {items_count_live:<5} | {valid_live:<5} | {elapsed_live:<7.2f}")

if __name__ == "__main__":
    run_smoke()
