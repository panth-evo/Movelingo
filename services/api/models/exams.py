from sqlalchemy import Column, String, Integer, JSON, DateTime, func, Boolean
from db import Base

class ExamPaperModel(Base):
    __tablename__ = "exam_papers"
    
    paper_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    spec_id = Column(String, index=True)
    scope = Column(String) # full, section, part
    status = Column(String) # generating, ready, failed
    parts_ready = Column(Integer, default=0)
    parts_total = Column(Integer, default=0)
    internal_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExamResultModel(Base):
    __tablename__ = "exam_results"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(String, index=True)
    skill = Column(String)
    level = Column(String)
    raw = Column(Integer)
    max_points = Column(Integer)
    ratio = Column(Integer) # or Float
    scaled_100 = Column(Integer)
    passed = Column(Boolean)
    pass_ratio = Column(Integer) # or Float
    per_part = Column(JSON)
    criteria = Column(JSON)
    summary = Column(String)
    ai_estimated = Column(Boolean, default=False)
    placed_level = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
