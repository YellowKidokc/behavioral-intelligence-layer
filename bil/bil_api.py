"""Behavioral Intelligence Layer — clean interface for all systems."""
import json
from datetime import datetime
from pathlib import Path

from bil.bil_models import ClipboardModel, ContentModel, FileModel, WebModel


class BIL:
    """Behavioral Intelligence Layer — learns from your behavior without labels."""

    def __init__(self, export_path: str = "exports"):
        self.models = {
            "web": WebModel(),
            "clipboard": ClipboardModel(),
            "files": FileModel(),
            "content": ContentModel(),
        }
        self.export_path = Path(export_path)
        self.export_path.mkdir(parents=True, exist_ok=True)

    def learn(self, model_name: str, features: dict, signal: float):
        """Feed a behavioral signal into a model.

        Args:
            model_name: web | clipboard | files | content
            features:   feature dict appropriate for the model
            signal:     0-1 binary or 0-10 gradient
        """
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}. Options: {list(self.models)}")
        self.models[model_name].learn(features, signal)
        self._log_event(model_name, features, signal)

    def predict(self, model_name: str, features: dict) -> float:
        """Get a relevance prediction (0-1) for given features."""
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")
        return self.models[model_name].predict(features)

    def predict_batch(self, model_name: str, feature_list: list[dict]) -> list[float]:
        """Predict relevance for a batch of items."""
        return [self.predict(model_name, f) for f in feature_list]

    def export_daily(self) -> str:
        """Generate a daily digest JSON for AI session context."""
        today = datetime.now().strftime("%Y-%m-%d")
        export_file = self.export_path / f"bil_digest_{today}.json"
        digest = {
            "date": today,
            "models": {name: model.get_summary() for name, model in self.models.items()},
        }
        export_file.write_text(json.dumps(digest, indent=2, default=str), encoding="utf-8")
        return str(export_file)

    def _log_event(self, model_name: str, features: dict, signal: float):
        """Log event to disk (Postgres optional — falls back to JSON log)."""
        try:
            log_file = self.export_path / "bil_events.jsonl"
            entry = {
                "ts": datetime.now().isoformat(),
                "model": model_name,
                "features": features,
                "signal": signal,
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass
