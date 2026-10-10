import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.llm_client import chat_text

router = APIRouter(prefix="/api/speech", tags=["speech"])
logger = logging.getLogger(__name__)

class PartnerTurnInput(BaseModel):
    spec_id: str
    part_no: int
    task_prompt: str
    format: str # 'pair' or 'examiner'
    language: str
    cefr: str
    learner_text: str

@router.post("/partner-turn")
def partner_turn(input_data: PartnerTurnInput):
    mode = os.environ.get("LLM_MODE", "mock").lower()
    if mode == "mock":
        return {"reply": "This is a canned reply for the speech partner in mock mode."}
        
    role = "the examiner" if input_data.format == "examiner" else "your conversation partner (another exam candidate)"
    
    system_prompt = (
        f"You are playing the role of {role} in a {input_data.cefr} speaking exam for the {input_data.language} language.\n"
        f"The task prompt is: {input_data.task_prompt}\n\n"
        "Rules:\n"
        "- Respond strictly in the target language.\n"
        f"- Maintain a {input_data.cefr} level vocabulary and grammar.\n"
        "- Reply in exactly 1 to 3 short, natural spoken sentences.\n"
        "- DO NOT correct the learner's mistakes during the exam. Just react naturally.\n"
        "- Stay strictly on the topic of the task prompt.\n"
        "- Keep the conversation moving forward by occasionally asking a relevant question."
    )
    
    user_prompt = f"Learner says: {input_data.learner_text}"
    
    try:
        reply = chat_text(system=system_prompt, user=user_prompt)
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Failed to get partner turn: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with AI partner.")
