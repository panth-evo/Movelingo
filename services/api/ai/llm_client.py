import os
import json
import time
import logging
import httpx
from pathlib import Path
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

class LLMError(Exception):
    pass

def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def _get_mock_response(task: str) -> dict:
    mock_file = Path(__file__).parent / "mock" / f"{task}.json"
    if mock_file.exists():
        try:
            with open(mock_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"_mock": True}

def generate_json(task: str, system: str, user: str, schema: dict, max_retries: int = 2) -> dict:
    mode = os.environ.get("LLM_MODE", "mock").lower()
    if mode == "mock":
        return _get_mock_response(task)

    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    schema_str = json.dumps(schema)
    system_prompt = f"{system}\n\nYou must respond ONLY with valid JSON that conforms to this schema:\n{schema_str}"
    
    current_user_prompt = user
    last_error = None
    
    for attempt in range(max_retries + 1):
        start_time = time.time()
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": current_user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            cleaned_content = _clean_json(content)
            parsed_json = json.loads(cleaned_content)
            
            validate(instance=parsed_json, schema=schema)
            
            latency = time.time() - start_time
            logger.info(f"Task: {task} | Attempt: {attempt + 1} | Latency: {latency:.2f}s | Status: Success")
            return parsed_json
            
        except httpx.HTTPError as e:
            latency = time.time() - start_time
            logger.error(f"Task: {task} | Attempt: {attempt + 1} | Latency: {latency:.2f}s | Status: HTTP Error: {str(e)}")
            last_error = e
            
        except json.JSONDecodeError as e:
            latency = time.time() - start_time
            error_msg = f"Failed to parse JSON: {str(e)}"
            logger.warning(f"Task: {task} | Attempt: {attempt + 1} | Latency: {latency:.2f}s | Status: Validation Failed")
            current_user_prompt = f"{user}\n\nYour last response was not valid JSON. Error: {error_msg}. Please fix it."
            last_error = e
            
        except ValidationError as e:
            latency = time.time() - start_time
            error_msg = f"JSON does not match schema: {e.message}"
            logger.warning(f"Task: {task} | Attempt: {attempt + 1} | Latency: {latency:.2f}s | Status: Validation Failed")
            current_user_prompt = f"{user}\n\nYour last response failed schema validation. Error: {error_msg}. Please fix it."
            last_error = e

    raise LLMError(f"Failed to generate valid JSON for task '{task}' after {max_retries + 1} attempts. Last error: {str(last_error)}")

def chat_text(system: str, user: str) -> str:
    mode = os.environ.get("LLM_MODE", "mock").lower()
    if mode == "mock":
        return "Canned reply for mock mode."
        
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    }
    
    start_time = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            
        data = response.json()
        latency = time.time() - start_time
        logger.info(f"Task: chat_text | Latency: {latency:.2f}s | Status: Success")
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"Task: chat_text | Latency: {latency:.2f}s | Status: Error: {str(e)}")
        raise LLMError(f"Failed chat_text completion: {str(e)}")
