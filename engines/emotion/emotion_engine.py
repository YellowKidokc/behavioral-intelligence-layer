"""
emotion_engine.py
BIL Emotion Engine — detects emotional tone and sentiment in text/content.

Uses Ollama to analyze:
  - Emotional valence (positive/negative/neutral)
  - Intensity (calm to urgent)
  - Dominant emotion (frustration, curiosity, excitement, boredom, etc.)
  - Context shifts (detected change in emotional state over time)

Applied to: clipboard captures, chat logs, article content, screenshot descriptions.
Feeds into the preference engine — emotional engagement = stronger signal.
"""
import json
import os
import requests
from datetime import datetime

BIL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BIL_ROOT, "bil_config.json")
EMOTION_LOG = os.path.join(BIL_ROOT, "data", "emotion", "emotion_events.jsonl")

os.makedirs(os.path.dirname(EMOTION_LOG), exist_ok=True)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def analyze(text: str, source: str = "unknown", model: str = "mistral") -> dict:
    """
    Analyze emotional tone of text.
    Returns: {valence, intensity, emotion, reasoning}
    """
    cfg = load_config()

    prompt = f"""Analyze the emotional tone of this text.

TEXT: {text[:1500]}

Reply in JSON:
{{
  "valence": "positive" or "negative" or "neutral" or "mixed",
  "intensity": 0.0-1.0 (0=calm, 1=extreme),
  "emotion": primary emotion (curiosity, frustration, excitement, boredom, anger, joy, anxiety, focus, confusion, satisfaction),
  "engagement": 0.0-1.0 (how emotionally invested is the author),
  "reasoning": "one sentence why"
}}"""

    try:
        r = requests.post(cfg["ollama_url"], json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        }, timeout=15)
        if r.ok:
            resp = r.json().get("response", "").strip()
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(resp[start:end])
                result["text_preview"] = text[:100]
                result["source"] = source
                result["ts"] = datetime.now().isoformat()
                result["model"] = model

                with open(EMOTION_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result) + "\n")

                return result
    except Exception as e:
        print(f"Emotion engine error: {e}")

    return {"valence": "neutral", "intensity": 0.0, "emotion": "unknown", "engagement": 0.0}


def detect_shift(recent_emotions: list[dict]) -> dict | None:
    """
    Detect emotional state changes over a series of events.
    Returns shift info if a significant change is detected, None otherwise.
    """
    if len(recent_emotions) < 3:
        return None

    recent = recent_emotions[-3:]
    intensities = [e.get("intensity", 0) for e in recent]
    emotions = [e.get("emotion", "unknown") for e in recent]

    # Check for intensity spike
    avg_early = sum(intensities[:-1]) / max(len(intensities) - 1, 1)
    latest = intensities[-1]

    if abs(latest - avg_early) > 0.3:
        direction = "escalating" if latest > avg_early else "calming"
        return {
            "shift": direction,
            "from_intensity": round(avg_early, 2),
            "to_intensity": round(latest, 2),
            "from_emotion": emotions[0],
            "to_emotion": emotions[-1],
            "ts": datetime.now().isoformat(),
        }

    # Check for emotion type change
    if len(set(emotions)) > 1 and emotions[-1] != emotions[0]:
        return {
            "shift": "emotion_change",
            "from_emotion": emotions[0],
            "to_emotion": emotions[-1],
            "ts": datetime.now().isoformat(),
        }

    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("BIL Emotion Engine")
        print("  python emotion_engine.py <text to analyze>")
    else:
        text = " ".join(sys.argv[1:])
        result = analyze(text, source="cli")
        print(f"Valence:    {result.get('valence')}")
        print(f"Intensity:  {result.get('intensity')}")
        print(f"Emotion:    {result.get('emotion')}")
        print(f"Engagement: {result.get('engagement')}")
        print(f"Reasoning:  {result.get('reasoning', '?')}")
