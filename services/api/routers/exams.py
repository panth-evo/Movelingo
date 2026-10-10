from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, Header
from typing import List, Optional
from pydantic import BaseModel
import logging

from engines.exams.spec_loader import load_all_specs, summarize
from engines.exams.assembler import create_paper_stub, generate_paper_async, get_public_paper

router = APIRouter(prefix="/api/exams", tags=["exams"])

class GenerateExamInput(BaseModel):
    language: str
    spec_id: str
    scope: str
    skill: Optional[str] = None
    part_no: Optional[int] = None
    topic_seed: Optional[str] = None

@router.get("/specs")
def get_specs(language: Optional[str] = Query(None, description="Language code to filter specs")) -> List[dict]:
    try:
        specs = load_all_specs()
    except Exception as e:
        logging.error(f"Failed to load specs: {e}")
        raise HTTPException(status_code=500, detail="Failed to load exam specifications")
        
    results = []
    for spec_id, spec in specs.items():
        if language is None or spec.get("language") == language:
            results.append(summarize(spec))
            
    return results

@router.post("/generate")
def generate_exam(input_data: GenerateExamInput, background_tasks: BackgroundTasks, x_user_id: str = Header(default="test_user")):
    try:
        paper = create_paper_stub(input_data.spec_id, input_data.scope, x_user_id)
        
        specs = load_all_specs()
        spec = specs.get(input_data.spec_id)
        
        background_tasks.add_task(
            generate_paper_async,
            paper_id=paper.paper_id,
            spec_id=input_data.spec_id,
            language=input_data.language,
            cefr=spec.get("cefr", "B1"),
            scope=input_data.scope,
            skill=input_data.skill,
            part_no=input_data.part_no,
            topic_seed=input_data.topic_seed
        )
        return {"paper_id": paper.paper_id, "status": "generating"}
    except Exception as e:
        logging.error(f"Generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers/{paper_id}")
def get_paper(paper_id: str):
    paper = get_public_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper
