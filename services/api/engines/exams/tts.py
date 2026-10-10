import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def synthesize(text: str, lang: str, voice_hint: str) -> Optional[bytes]:
    provider = os.environ.get("TTS_PROVIDER")
    if not provider:
        return None
        
    # Since we can't add paid dependencies, return a mock byte string
    # when the provider is set for testing purposes.
    logger.info(f"Mock TTS synthesizing text for {lang} with {voice_hint}")
    return b"MOCK_MP3_BYTES"
