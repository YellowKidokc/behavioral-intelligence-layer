"""
vision_engine.py
BIL Vision Engine — understands images via Ollama vision models.

Uses moondream (fast, 1.7GB) for quick descriptions.
Uses llava (better detail) for deeper analysis when needed.

Capabilities:
  - Describe what's on screen (app, content, user activity)
  - OCR-style text extraction from screenshots
  - Compare two screenshots for changes
  - Classify image content (code, article, chat, video, etc.)
"""
import base64
import json
import os
import requests
from datetime import datetime

BIL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BIL_ROOT, "bil_config.json")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def describe(image_path: str, model: str = "moondream", prompt: str = None) -> str:
    """Describe what's on screen in one sentence."""
    cfg = load_config()
    if prompt is None:
        prompt = "One sentence: what app is open and what is the user doing?"

    try:
        r = requests.post(cfg["ollama_url"], json={
            "model": model,
            "prompt": prompt,
            "images": [_encode_image(image_path)],
            "stream": False,
        }, timeout=30)
        if r.ok:
            return r.json().get("response", "").strip()
    except Exception as e:
        print(f"Vision error: {e}")
    return ""


def extract_text(image_path: str, model: str = "moondream") -> str:
    """Extract visible text from a screenshot."""
    return describe(image_path, model,
        "Read and transcribe all visible text in this image. Include menu items, "
        "titles, body text, code, URLs. Return the text only, no commentary.")


def classify(image_path: str, model: str = "moondream") -> dict:
    """Classify the content type of a screenshot."""
    cfg = load_config()

    try:
        r = requests.post(cfg["ollama_url"], json={
            "model": model,
            "prompt": 'Classify this screenshot into exactly one category: code, article, chat, video, social, email, terminal, spreadsheet, design, search, file_manager, settings, other. Reply with JSON: {"category": "...", "app": "...", "confidence": 0.0-1.0}',
            "images": [_encode_image(image_path)],
            "stream": False,
        }, timeout=20)
        if r.ok:
            text = r.json().get("response", "").strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
    except Exception:
        pass
    return {"category": "unknown", "app": "unknown", "confidence": 0.0}


def compare(image_a: str, image_b: str, model: str = "moondream") -> str:
    """Describe what changed between two screenshots."""
    cfg = load_config()

    desc_a = describe(image_a, model)
    desc_b = describe(image_b, model)

    try:
        r = requests.post(cfg["ollama_url"], json={
            "model": "mistral",
            "prompt": f"Two consecutive screenshots were described:\nBEFORE: {desc_a}\nAFTER: {desc_b}\n\nIn one sentence, what changed?",
            "stream": False,
        }, timeout=15)
        if r.ok:
            return r.json().get("response", "").strip()
    except Exception:
        pass
    return f"Before: {desc_a} | After: {desc_b}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("BIL Vision Engine")
        print("  python vision_engine.py describe <image>")
        print("  python vision_engine.py ocr <image>")
        print("  python vision_engine.py classify <image>")
        print("  python vision_engine.py compare <image_a> <image_b>")
    elif sys.argv[1] == "describe":
        print(describe(sys.argv[2]))
    elif sys.argv[1] == "ocr":
        print(extract_text(sys.argv[2]))
    elif sys.argv[1] == "classify":
        print(json.dumps(classify(sys.argv[2]), indent=2))
    elif sys.argv[1] == "compare" and len(sys.argv) >= 4:
        print(compare(sys.argv[2], sys.argv[3]))
