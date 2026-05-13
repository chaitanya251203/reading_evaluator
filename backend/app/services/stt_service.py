"""
STT Service — uses Bhashini API for Hindi and English transcription.
"""
import os
import logging
import base64
import requests
import wave
from typing import Optional

logger = logging.getLogger(__name__)

BHASHINI_ENDPOINT = os.getenv("BHASHINI_ENDPOINT_URL", "https://dhruva-api.bhashini.gov.in/services/inference/pipeline")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "")

_LANG_MAPPING = {
    "hi": "ai4bharat/conformer-hi-gpu--t4",
    "en": "ai4bharat/whisper-medium-en--gpu--t4"
}

def _get_bhashini_lang_config(language: Optional[str]):
    l = (language or "english").lower()
    if "hindi" in l or l == "hi":
        return "hi", _LANG_MAPPING["hi"]
    return "en", _LANG_MAPPING["en"]

def _get_audio_duration(file_path: str) -> float:
    try:
        with wave.open(file_path, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate)
    except Exception as e:
        logger.warning(f"Could not read audio duration: {e}")
        return 1.0

def transcribe_audio(file_path: str, language: Optional[str] = None) -> dict:
    if not BHASHINI_API_KEY:
        logger.error("BHASHINI_API_KEY is not set.")
        return {"text": "", "segments": [], "duration_seconds": 1.0, "avg_logprob": -0.2}

    lang_code, service_id = _get_bhashini_lang_config(language)
    duration = _get_audio_duration(file_path)

    try:
        with open(file_path, "rb") as f:
            encoded_audio = base64.b64encode(f.read()).decode("utf-8")

        headers = {
            "Authorization": BHASHINI_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": lang_code},
                        "serviceId": service_id,
                        "audioFormat": "wav",
                        "samplingRate": 16000
                    }
                }
            ],
            "inputData": {
                "audio": [{"audioContent": encoded_audio}]
            }
        }

        resp = requests.post(BHASHINI_ENDPOINT, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Bhashini returns text in pipelineResponse -> output[0] -> source
        text = ""
        if "pipelineResponse" in data and data["pipelineResponse"]:
            output = data["pipelineResponse"][0].get("output", [])
            if output:
                text = output[0].get("source", "")

        # Bhashini doesn't give segments or logprobs currently in this endpoint
        # We will generate a single dummy segment so fluency scoring doesn't crash
        segment = {
            "start": 0.0,
            "end": duration,
            "text": text,
            "avg_logprob": -0.1
        }

        return {
            "text": text,
            "segments": [segment] if text else [],
            "duration_seconds": duration,
            "avg_logprob": -0.1,
        }

    except Exception as e:
        logger.error(f"Bhashini transcription failed: {e}")
        return {
            "text": "",
            "segments": [],
            "duration_seconds": duration,
            "avg_logprob": -0.2,
        }
