"""
media_router.py — Station: Media Transformation Router

After classification, determines WHAT FORM the content should take.
Not "what is it?" (that's the classifier) — "what should it BECOME?"

Routes to media-specific sub-pipelines:
  - Text track:  markdown/HTML → lossless → grade → publish
  - Audio track: script → TTS render → audio QA → R2
  - Video track: script → video render → upload
  - Data track:  raw data → normalize → warehouse → visualization
  - Hybrid:      some content needs MULTIPLE forms (paper + TTS + thumbnail)

The key insight: a single paper might need to become THREE things.
A Convergence article needs: HTML (web), TTS (podcast), thumbnail (social).
So this station doesn't just ROUTE — it can FORK into parallel tracks.
"""

import json
from pathlib import Path
from typing import Optional

from ..station_base import StationBase, StationVerdict, Manifest, SignalType


# ── Media type detection rules ────────────────────────────────
MEDIA_RULES = {
    "text_to_html": {
        "input_ext": [".md", ".txt"],
        "doc_types": ["paper", "article", "note"],
        "output_dir": "html-queue",
        "description": "Markdown/text → HTML page",
    },
    "text_to_tts": {
        "input_ext": [".md", ".txt", ".html"],
        "doc_types": ["article", "paper"],
        "keywords": ["podcast", "narration", "audio", "tts", "episode"],
        "output_dir": "tts-queue",
        "description": "Written content → TTS audio file",
    },
    "text_to_video": {
        "input_ext": [".md", ".txt"],
        "doc_types": ["article"],
        "keywords": ["video", "youtube", "visual", "slides"],
        "output_dir": "video-queue",
        "description": "Script → video with slides/visuals",
    },
    "audio_to_text": {
        "input_ext": [".mp3", ".wav", ".m4a", ".ogg", ".webm"],
        "doc_types": [],
        "output_dir": "transcripts",
        "description": "Audio recording → text transcript",
    },
    "data_normalize": {
        "input_ext": [".csv", ".json", ".tsv", ".xlsx"],
        "doc_types": ["data"],
        "output_dir": "data-normalized",
        "description": "Raw data → cleaned, normalized, warehouse-ready",
    },
    "generate_thumbnail": {
        "input_ext": [".md", ".html"],
        "doc_types": ["article", "paper"],
        "keywords": ["publish", "substack", "social"],
        "output_dir": "thumbnails",
        "description": "Content → social media thumbnail image",
    },
}


class MediaRouterStation(StationBase):
    """
    Routes content to the correct media transformation track(s).
    Can fork a single file into multiple parallel tracks.
    """

    def __init__(self, input_dir: str, output_dir: str,
                 media_root: str = r"D:\FAP\media", **kwargs):
        super().__init__(
            name="media-router",
            input_dir=input_dir,
            output_dir=output_dir,
            file_extensions=["*"],
            **kwargs,
        )
        self.media_root = Path(media_root)
        self.media_root.mkdir(parents=True, exist_ok=True)

        # Create all media subdirs
        for rule in MEDIA_RULES.values():
            (self.media_root / rule["output_dir"]).mkdir(parents=True, exist_ok=True)

    def process(self, file_path: Path, manifest: Manifest) -> tuple:
        # Read classification from sidecar if available
        sidecar = file_path.with_suffix(file_path.suffix + ".fap.json")
        classification = {}
        if sidecar.exists():
            try:
                classification = json.loads(sidecar.read_text())
            except Exception:
                pass

        doc_type = classification.get("doc_type",
                   manifest.metadata.get("doc_type", "unknown"))

        # Determine applicable media routes
        routes = self._determine_routes(file_path, doc_type, classification)

        if not routes:
            # Default: pass through to text track
            manifest.metadata["media_routes"] = ["text_to_html"]
            return (StationVerdict.PASS, 0.6,
                    "No specific media route detected, defaulting to text track")

        # Fork: copy file to each media track
        import shutil
        forked_to = []
        for route_name in routes:
            rule = MEDIA_RULES.get(route_name, {})
            dest_dir = self.media_root / rule.get("output_dir", "unknown")
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / file_path.name
            if not dest.exists():
                shutil.copy2(str(file_path), str(dest))
                # Copy sidecar too
                if sidecar.exists():
                    shutil.copy2(str(sidecar), str(dest.with_suffix(dest.suffix + ".fap.json")))
                forked_to.append(str(dest))

        manifest.metadata["media_routes"] = routes
        manifest.metadata["forked_to"] = forked_to

        # Signal for each fork
        for route in routes:
            self.emit_signal(
                SignalType.UPSTREAM,
                f"{file_path.name} forked to {route}",
                {"route": route, "file": str(file_path)},
            )

        return (StationVerdict.PASS, 0.85,
                f"Routed to {len(routes)} track(s): {', '.join(routes)}")

    def _determine_routes(self, file_path: Path, doc_type: str,
                          classification: dict) -> list[str]:
        routes = []
        ext = file_path.suffix.lower()

        for route_name, rule in MEDIA_RULES.items():
            score = 0

            # Extension match
            if ext in rule.get("input_ext", []):
                score += 1

            # Doc type match
            if doc_type in rule.get("doc_types", []):
                score += 2

            # Keyword match (check file content hints)
            keywords = rule.get("keywords", [])
            if keywords:
                # Check filename
                fname_lower = file_path.stem.lower()
                if any(kw in fname_lower for kw in keywords):
                    score += 3

                # Check classification metadata
                topics = classification.get("ollama", {}).get("topics", [])
                if any(kw in " ".join(topics).lower() for kw in keywords):
                    score += 2

            if score >= 2:
                routes.append(route_name)

        return routes
