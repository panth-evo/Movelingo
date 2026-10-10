import uuid
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from db import SessionLocal
from models.exams import ExamPaperModel
from engines.exams.spec_loader import get_spec
from engines.exams.generator import generate_part

def create_paper_stub(spec_id: str, scope: str, user_id: str) -> ExamPaperModel:
    paper_id = str(uuid.uuid4())
    spec = get_spec(spec_id)
    
    parts_total = 0
    sections_to_gen = []
    for section in spec.get("sections", []):
        if scope in ["full", "section"]: 
            parts_total += len(section.get("parts", []))
            
    if scope == "part":
        parts_total = 1

    db = SessionLocal()
    paper = ExamPaperModel(
        paper_id=paper_id,
        user_id=user_id,
        spec_id=spec_id,
        scope=scope,
        status="generating",
        parts_ready=0,
        parts_total=parts_total,
        internal_json={
            "paper_id": paper_id,
            "spec_id": spec_id,
            "language": spec.get("language"),
            "cefr": spec.get("cefr"),
            "exam_name": spec.get("exam_name"),
            "derived": spec.get("derived", False),
            "status": "generating",
            "parts_ready": 0,
            "parts_total": parts_total,
            "sections": []
        }
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    db.close()
    return paper

async def generate_paper_async(paper_id: str, spec_id: str, language: str, cefr: str, scope: str, skill: Optional[str]=None, part_no: Optional[int]=None, topic_seed: Optional[str]=None):
    spec = get_spec(spec_id)
    
    with SessionLocal() as db:
        paper_model = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
        if not paper_model:
            return

    internal_sections = []
    tasks = []
    parts_to_generate = []
    
    for section in spec.get("sections", []):
        if scope == "section" and section.get("skill") != skill:
            continue
            
        sec_data = {
            "skill": section["skill"],
            "duration_min": section["duration_min"],
            "parts": []
        }
        internal_sections.append(sec_data)
        
        for part in section.get("parts", []):
            if scope == "part" and (section.get("skill") != skill or part.get("part_no") != part_no):
                continue
                
            parts_to_generate.append((sec_data, section, part))

    async def _gen_worker(sec_data: dict, current_section: dict, current_part: dict):
        try:
            generated = await asyncio.to_thread(
                generate_part, spec, current_section, current_part, topic_seed, language, cefr
            )
        except Exception as e:
            generated = {"_failed": True, "error": str(e), "passage": "Generation failed."}
            
        merged_part = {**current_part, **generated}
        sec_data["parts"].append(merged_part)
        
        with SessionLocal() as s:
            p = s.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
            if p:
                p.parts_ready += 1
                s.commit()

    semaphore = asyncio.Semaphore(4)
    async def sem_task(task):
        async with semaphore:
            await task
            
    for sec_data, current_section, current_part in parts_to_generate:
        tasks.append(_gen_worker(sec_data, current_section, current_part))
        
    await asyncio.gather(*(sem_task(t) for t in tasks))
    
    with SessionLocal() as db:
        paper_model = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
        if paper_model:
            internal_json = paper_model.internal_json.copy()
            internal_json["sections"] = internal_sections
            internal_json["status"] = "ready"
            internal_json["parts_ready"] = paper_model.parts_ready
            
            paper_model.internal_json = internal_json
            paper_model.status = "ready"
            db.commit()

def get_public_paper(paper_id: str) -> dict:
    db = SessionLocal()
    paper_model = db.query(ExamPaperModel).filter(ExamPaperModel.paper_id == paper_id).first()
    db.close()
    
    if not paper_model:
        return None
        
    internal = paper_model.internal_json
    public = internal.copy()
    
    public_sections = []
    for section in public.get("sections", []):
        pub_sec = section.copy()
        pub_parts = []
        for part in section.get("parts", []):
            pub_part = part.copy()
            if "items" in pub_part:
                pub_items = []
                for item in pub_part["items"]:
                    pub_item = item.copy()
                    if "options" in pub_item:
                        pub_options = []
                        for opt in pub_item["options"]:
                            pub_opt = opt.copy()
                            pub_opt.pop("is_correct", None)
                            pub_options.append(pub_opt)
                        pub_item["options"] = pub_options
                    pub_items.append(pub_item)
                pub_part["items"] = pub_items
            pub_parts.append(pub_part)
        pub_sec["parts"] = pub_parts
        public_sections.append(pub_sec)
        
    public["sections"] = public_sections
    return public
