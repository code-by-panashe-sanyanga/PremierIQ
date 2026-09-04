from __future__ import annotations

import json
import os

import httpx
from pydantic import BaseModel, Field

MODEL = "gemini-3.8-flash"
INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


class MatchBrief(BaseModel):
    headline: str = Field(description="One punchy sentence on who is favoured, faithful to the numbers.")
    analysis: str = Field(description="Two sentences of editorial analysis. No invented injuries, lineups, transfers, or suspensions.")


def available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def _api_key() -> str:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


def _prompt(payload: dict) -> str:
    return (
        "You are PremierIQ, a Premier League match analyst writing an IQ briefing. "
        "Use only the supplied Monte Carlo numbers and context. "
        "Do not invent injuries, lineups, transfers, suspensions, or match events. "
        "Formation values are simulation assumptions, not confirmed team sheets. "
        "Do not give betting advice or imply certainty.\n\n"
        f"{json.dumps(payload)}"
    )


def _response_format() -> list[dict]:
    return [
        {
            "type": "text",
            "mime_type": "application/json",
            "schema": MatchBrief.model_json_schema(),
        }
    ]


def _text_from_interaction(data: object) -> str:
    if data is None:
        return ""
    text = getattr(data, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    if isinstance(data, dict):
        if isinstance(data.get("output_text"), str) and data["output_text"].strip():
            return data["output_text"].strip()
        outputs = data.get("outputs") or data.get("steps") or []
        chunks: list[str] = []
        for item in outputs:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "model_output":
                content = item.get("content") or item.get("text") or ""
                if isinstance(content, str):
                    chunks.append(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("text"):
                            chunks.append(str(part["text"]))
                        elif isinstance(part, str):
                            chunks.append(part)
        return "\n".join(chunks).strip()
    return ""


def _via_sdk(prompt: str) -> str:
    from google import genai

    client = genai.Client()
    interactions = getattr(client, "interactions", None)
    if interactions is None:
        raise AttributeError("interactions API not in this google-genai build")
    interaction = interactions.create(
        model=MODEL,
        input=prompt,
        response_format=_response_format(),
        generation_config={"thinking_level": "low"},
    )
    return _text_from_interaction(interaction)


def _via_rest(prompt: str) -> str:
    response = httpx.post(
        INTERACTIONS_URL,
        headers={"x-goog-api-key": _api_key(), "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "input": prompt,
            "response_format": _response_format(),
            "generation_config": {"thinking_level": "low"},
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return _text_from_interaction(response.json())


def _via_generate_content(prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MatchBrief,
        ),
    )
    return (response.text or "").strip()


def brief_prediction(payload: dict) -> dict | None:
    if not available():
        return None
    prompt = _prompt(payload)
    text = ""
    for call in (_via_sdk, _via_rest, _via_generate_content):
        try:
            text = call(prompt)
            if text:
                break
        except Exception:
            continue
    if not text:
        return None
    brief = MatchBrief.model_validate_json(text)
    return {"model": MODEL, **brief.model_dump()}
