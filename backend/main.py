# backend/main.py
import os
import json
from datetime import datetime
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.api.db import journal_collection  # your MongoDB collection

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Set OPENROUTER_API_KEY in .env")

app = FastAPI(title="Journal POC API (OpenRouter)")

# -----------------------------
# Pydantic Models
# -----------------------------
class EntryCreate(BaseModel):
    text: str

class EntryOut(BaseModel):
    id: str
    original_text: str
    corrected_text: Optional[str]
    ai_insights: Optional[dict]
    mood: Optional[str]
    mood_score: Optional[int]
    created_at: datetime

# -----------------------------
# OpenRouter Analyzer
# -----------------------------
def call_openrouter_analyze(entry_text: str) -> dict:
    """
    Call OpenRouter free models to analyze journal entry.
    """
    system_prompt = (
        "You are an empathetic journaling assistant. "
        "Return ONLY a JSON object with these fields:\n"
        "  corrected_text\n"
        "  sentiment\n"
        "  mood_score\n"
        "  themes\n"
        "  insights\n"
        "  follow_up_prompts\n"
        "  supportive_message\n"
    )

    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": entry_text}
        ],
        "temperature": 0.7
    }

    response = requests.post(
        os.getenv("OPENROUTER_URI"),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost:8001",
            "X-Title": "Journal Assistant POC"
        },
        json=payload
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"OpenRouter error: {response.text}")

    result = response.json()
    assistant_text = result["choices"][0]["message"]["content"]

    # Parse JSON safely
    try:
        return json.loads(assistant_text)
    except Exception:
        import re
        m = re.search(r"(\{.*\})", assistant_text, flags=re.S)
        if not m:
            raise ValueError("OpenRouter did not return valid JSON.")
        return json.loads(m.group(1))

# -----------------------------
# API: Create Journal Entry
# -----------------------------
@app.post("/entries", response_model=EntryOut)
def create_entry(payload: EntryCreate):
    ai_result = call_openrouter_analyze(payload.text)

    doc = {
        "original_text": payload.text,
        "corrected_text": ai_result.get("corrected_text"),
        "ai_insights": {
            "themes": ai_result.get("themes"),
            "insights": ai_result.get("insights"),
            "follow_up_prompts": ai_result.get("follow_up_prompts"),
            "supportive_message": ai_result.get("supportive_message"),
        },
        "mood": ai_result.get("sentiment"),
        "mood_score": int(ai_result.get("mood_score") or 0),
        "created_at": datetime.utcnow(),
    }

    inserted = journal_collection.insert_one(doc)
    doc["id"] = str(inserted.inserted_id)

    return EntryOut(**doc)

# -----------------------------
# API: List Entries
# -----------------------------
@app.get("/entries", response_model=List[EntryOut])
def list_entries(limit: int = 50):
    cursor = journal_collection.find().sort("created_at", -1).limit(limit)

    entries = []
    for d in cursor:
        entries.append(
            EntryOut(
                id=str(d["_id"]),
                original_text=d["original_text"],
                corrected_text=d.get("corrected_text"),
                ai_insights=d.get("ai_insights"),
                mood=d.get("mood"),
                mood_score=d.get("mood_score"),
                created_at=d.get("created_at"),
            )
        )
    return entries

# -----------------------------
# API: Analytics
# -----------------------------
@app.get("/analytics")
def analytics():
    cursor = journal_collection.find().sort("created_at", 1)

    timeline = []
    scores = []

    for d in cursor:
        score = d.get("mood_score", 0)
        scores.append(score)
        timeline.append({
            "created_at": d["created_at"].isoformat(),
            "mood_score": score
        })

    avg = sum(scores) / (len(scores) or 1)

    return {
        "count": len(scores),
        "avg_mood_score": avg,
        "timeline": timeline
    }
