from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, Header
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Union
from pydantic import BaseModel
import logging
import os
from pathlib import Path

from engines.exams.spec_loader import load_all_specs, summarize, get_spec
from engines.exams.assembler import create_paper_stub, generate_paper_async, get_public_paper
from engines.exams.tts import synthesize
from engines.exams.grader import grade_objective, grade_subjective
from db import SessionLocal
from models.exams import ExamPaperModel, ExamResultModel

router = APIRouter(prefix="/api/exams", tags=["exams"])

class GenerateExamInput(BaseModel):
    language: str
    spec_id: str
    scope: str
    skill: Optional[str] = None
    part_no: Optional[int] = None
    topic_seed: Optional[str] = None

class SubmitExamInput(BaseModel):
    answers: Dict[str, Union[List[str], str]]
    skill: str

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

@router.get("/papers/{paper_id}/audio/{part_no}/{segment_id}")
def get_audio(paper_id: str, part_no: int, segment_id: str):
    cache_dir = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "audio" / paper_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / f"part_{part_no}_{segment_id}.mp3"
    
    if file_path.exists():
        return FileResponse(file_path, media_type="audio/mpeg")
        
    db = SessionLocal()
    paper_model = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
    db.close()
    
    if not paper_model:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    target_segment = None
    lang = paper_model.internal_json.get("language", "de")
    for section in paper_model.internal_json.get("sections", []):
        if section.get("skill") != "listening":
            continue
        for part in section.get("parts", []):
            if part.get("part_no") == part_no:
                segments = part.get("audio", {}).get("segments", [])
                for seg in segments:
                    if seg.get("segment_id") == segment_id:
                        target_segment = seg
                        break
                        
    if not target_segment:
        raise HTTPException(status_code=404, detail="Segment not found")
        
    script = target_segment.get("script", [])
    if not script:
        raise HTTPException(status_code=404, detail="Script is empty")
        
    full_text = " ".join([line.get("text", "") for line in script])
    voice_hint = script[0].get("voice_hint", "female_1") if script else "female_1"
    
    audio_bytes = synthesize(full_text, lang, voice_hint)
    
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="TTS Provider not configured")
        
    with open(file_path, "wb") as f:
        f.write(audio_bytes)
        
    return FileResponse(file_path, media_type="audio/mpeg")

@router.post("/papers/{paper_id}/submit")
def submit_paper(paper_id: str, input_data: SubmitExamInput, x_user_id: str = Header(default="test_user")):
    db = SessionLocal()
    paper_model = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
    
    if not paper_model:
        db.close()
        raise HTTPException(status_code=404, detail="Paper not found")
        
    internal_json = paper_model.internal_json
    spec = get_spec(internal_json.get("spec_id"))
    
    target_section = next((s for s in internal_json.get("sections", []) if s.get("skill") == input_data.skill), None)
    spec_section = next((s for s in spec.get("sections", []) if s.get("skill") == input_data.skill), None)
    
    if not target_section or not spec_section:
        db.close()
        raise HTTPException(status_code=404, detail="Skill section not found in paper")
        
    pass_ratio = spec.get("pass_ratio", 0.6)
    scale_to = spec.get("scale_to", 100)
    cefr = spec.get("cefr", "B1")
    language = spec.get("language", "de")
    
    if input_data.skill in ["reading", "listening"]:
        result = grade_objective(spec_section, target_section, input_data.answers, pass_ratio, scale_to)
        attempted = sum(len(p.get("items", [])) for p in target_section.get("parts", []))
        correct = result["raw"]
    else:
        result = grade_subjective(spec_section, target_section, input_data.answers, cefr, language, pass_ratio, scale_to)
        num_tasks = len(target_section.get("parts", []))
        attempted = 6 * num_tasks
        correct = round(attempted * result["ratio"])
        
    result_model = ExamResultModel(
        paper_id=paper_id,
        skill=input_data.skill,
        level=cefr,
        raw=result["raw"],
        max_points=result["max_points"],
        ratio=result["ratio"],
        scaled_100=result["scaled_100"],
        passed=result["passed"],
        pass_ratio=result["pass_ratio"],
        per_part=result["per_part"],
        criteria=result.get("criteria", []),
        summary=result.get("summary", ""),
        ai_estimated=result.get("ai_estimated", False)
    )
    db.add(result_model)
    db.commit()
    db.refresh(result_model)
    db.close()
    
    try:
        from engines.progress.progress_engine import record_progress_event, compute_progress
        record_progress_event(
            user_id=x_user_id,
            language=language,
            skill=input_data.skill,
            level=cefr,
            attempted=attempted,
            correct=correct,
            section_ratio=result["ratio"],
            passed=result["passed"]
        )
        progress = compute_progress(x_user_id, language)
    except ImportError:
        progress = {"_stub": True, "message": "Progress engine not linked yet"}
        
    return {
        "result_id": result_model.id,
        "skill": input_data.skill,
        "score": result["scaled_100"],
        "passed": result["passed"],
        "details": result,
        "progress": progress
    }
    
@router.get("/results")
def get_results(language: str, x_user_id: str = Header(default="test_user")):
    db = SessionLocal()
    results = db.query(ExamResultModel).order_by(ExamResultModel.created_at.desc()).limit(20).all()
    db.close()
    
    return [
        {
            "id": r.id,
            "paper_id": r.paper_id,
            "skill": r.skill,
            "level": r.level,
            "scaled_100": r.scaled_100,
            "passed": r.passed
        } for r in results
    ]
