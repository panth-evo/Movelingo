import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db import SessionLocal, Base, engine
from models.exams import ExamPaperModel
from engines.exams.assembler import get_public_paper

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m engines.exams.check_paper <paper_id>")
        return
        
    paper_id = sys.argv[1]
    paper = get_public_paper(paper_id)
    
    if not paper:
        print("Paper not found.")
        return
        
    print(f"Paper ID: {paper['paper_id']}")
    print(f"Spec ID: {paper['spec_id']} | Language: {paper.get('language')} | CEFR: {paper.get('cefr')}")
    print(f"Status: {paper.get('status')} ({paper.get('parts_ready')}/{paper.get('parts_total')} ready)")
    print("-" * 50)
    
    for section in paper.get("sections", []):
        print(f"SECTION: {section.get('skill', '').upper()} ({section.get('duration_min')} min)")
        for part in section.get("parts", []):
            print(f"  Part {part.get('part_no')}: {part.get('task_type')} ({part.get('item_count')} items)")
            
            passage = part.get("passage", "")
            word_count = 0
            if isinstance(passage, list):
                word_count = sum(len(str(p).split()) for p in passage)
            else:
                word_count = len(str(passage).split())
                
            print(f"    Words: {word_count}")
            
            items = part.get("items", [])
            types = set(i.get("type") for i in items)
            print(f"    Types present: {', '.join(types) if types else 'None'}")
            
            if "error" in part:
                print(f"    ERROR: {part['error']}")
                
        print()

if __name__ == "__main__":
    main()
