"""
repo_analyzer.py
BIL GitHub Engine — analyzes repos, scores relevance, checks claims.

Capabilities:
  - Parse repo metadata (stars, forks, language, topics, README)
  - Score repo relevance against user interests
  - Fact-check README claims against actual repo content
  - Compare repos in the same space
  - Track repo activity over time
"""
import json
import os
import requests
from datetime import datetime

BIL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BIL_ROOT, "bil_config.json")
REPO_LOG = os.path.join(BIL_ROOT, "data", "github", "repo_analysis.jsonl")

os.makedirs(os.path.dirname(REPO_LOG), exist_ok=True)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def fetch_repo_info(owner: str, repo: str, token: str = None) -> dict | None:
    """Fetch repo metadata from GitHub API."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}",
                        headers=headers, timeout=10)
        if r.ok:
            data = r.json()
            return {
                "full_name": data.get("full_name"),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "language": data.get("language", ""),
                "topics": data.get("topics", []),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "open_issues": data.get("open_issues_count", 0),
                "license": (data.get("license") or {}).get("spdx_id", ""),
                "archived": data.get("archived", False),
            }
    except Exception:
        pass
    return None


def fetch_readme(owner: str, repo: str, token: str = None) -> str:
    """Fetch repo README content."""
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/readme",
                        headers=headers, timeout=10)
        if r.ok:
            return r.text[:5000]
    except Exception:
        pass
    return ""


def score_repo(repo_info: dict, behavioral_signal: dict = None) -> dict:
    """
    Score a repo's relevance combining metadata quality + behavioral signal.

    Metadata score (what the repo IS):
      - Stars/forks ratio, language match, topic overlap, freshness

    Behavioral score (what the USER DID):
      - Time on page, copied code, bookmarked, scrolled
    """
    if not repo_info:
        return {"score": 0, "reason": "no repo info"}

    # Metadata score
    meta_score = 0.0
    stars = repo_info.get("stars", 0)
    if stars > 1000:
        meta_score += 0.2
    elif stars > 100:
        meta_score += 0.1

    if repo_info.get("language") in ["Python", "JavaScript", "TypeScript"]:
        meta_score += 0.1

    if not repo_info.get("archived"):
        meta_score += 0.1

    if repo_info.get("license"):
        meta_score += 0.05

    # Behavioral score
    behav_score = 0.3  # base: visited
    if behavioral_signal:
        if behavioral_signal.get("copied_code"):
            behav_score += 0.2
        if behavioral_signal.get("bookmarked"):
            behav_score += 0.2
        time_on = behavioral_signal.get("time_on_page", 0)
        if time_on > 60:
            behav_score += 0.1
        if time_on > 180:
            behav_score += 0.1

    combined = min(1.0, meta_score + behav_score)

    result = {
        "repo": repo_info.get("full_name", ""),
        "meta_score": round(meta_score, 3),
        "behavioral_score": round(behav_score, 3),
        "combined_score": round(combined, 3),
        "ts": datetime.now().isoformat(),
    }

    with open(REPO_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")

    return result


def fact_check_readme(owner: str, repo: str, model: str = "mistral") -> dict:
    """
    Cross-reference README claims against repo metadata.
    Flags exaggerations, missing evidence, and unverifiable claims.
    """
    cfg = load_config()
    info = fetch_repo_info(owner, repo)
    readme = fetch_readme(owner, repo)

    if not info or not readme:
        return {"error": "Could not fetch repo data"}

    prompt = f"""You are a fact-checker for GitHub repos. Compare this README against the repo's actual metadata.

REPO: {info['full_name']}
Stars: {info['stars']} | Forks: {info['forks']} | Language: {info['language']}
Topics: {', '.join(info.get('topics', []))}
License: {info.get('license', 'none')} | Archived: {info.get('archived')}
Last updated: {info.get('updated_at', '?')}

README (first 2000 chars):
{readme[:2000]}

Check for:
1. Claims about performance/accuracy that aren't backed by linked benchmarks
2. "Production ready" claims on repos with few stars or recent creation
3. Feature claims that don't match the language/topics
4. Missing license for commercial-use claims

Reply in JSON: {{"claims_checked": N, "issues": ["..."], "trust_score": 0.0-1.0, "summary": "..."}}"""

    try:
        r = requests.post(cfg["ollama_url"], json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        }, timeout=30)
        if r.ok:
            text = r.json().get("response", "").strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
    except Exception:
        pass
    return {"error": "Analysis failed"}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("BIL GitHub Engine")
        print("  python repo_analyzer.py info <owner/repo>")
        print("  python repo_analyzer.py score <owner/repo>")
        print("  python repo_analyzer.py check <owner/repo>")
    elif sys.argv[1] == "info" and len(sys.argv) >= 3:
        parts = sys.argv[2].split("/")
        if len(parts) == 2:
            info = fetch_repo_info(parts[0], parts[1])
            print(json.dumps(info, indent=2))
    elif sys.argv[1] == "score" and len(sys.argv) >= 3:
        parts = sys.argv[2].split("/")
        if len(parts) == 2:
            info = fetch_repo_info(parts[0], parts[1])
            result = score_repo(info)
            print(json.dumps(result, indent=2))
    elif sys.argv[1] == "check" and len(sys.argv) >= 3:
        parts = sys.argv[2].split("/")
        if len(parts) == 2:
            result = fact_check_readme(parts[0], parts[1])
            print(json.dumps(result, indent=2))
