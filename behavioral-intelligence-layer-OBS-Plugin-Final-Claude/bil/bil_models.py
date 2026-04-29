"""River-based online learning models for behavioral intelligence."""
from river import compose, linear_model, preprocessing


class BaseModel:
    def __init__(self):
        self.model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LogisticRegression(),
        )
        self.event_count = 0

    def learn(self, features: dict, signal: float):
        y = 1 if signal > 0.5 else 0
        self.model.learn_one(features, y)
        self.event_count += 1

    def predict(self, features: dict) -> float:
        return self.model.predict_proba_one(features).get(True, 0.5)

    def get_summary(self) -> dict:
        return {"event_count": self.event_count, "type": self.__class__.__name__}


class WebModel(BaseModel):
    def learn(self, features, signal):
        super().learn(self._flatten(features), signal)

    def predict(self, features):
        return super().predict(self._flatten(features))

    def _flatten(self, features):
        flat = {}
        for k, v in features.items():
            if k == "top_keywords":
                if isinstance(v, list):
                    for kw in v:
                        flat[f"kw_{kw}"] = 1
            elif isinstance(v, bool):
                flat[k] = 1 if v else 0
            elif isinstance(v, (int, float)):
                flat[k] = v
            elif isinstance(v, str):
                flat[f"{k}_{v}"] = 1
        return flat


class ClipboardModel(BaseModel):
    def learn(self, features, signal):
        super().learn(self._flatten(features), signal)

    def predict(self, features):
        return super().predict(self._flatten(features))

    def _flatten(self, features):
        flat = {}
        for k, v in features.items():
            if k == "text_keywords" and isinstance(v, list):
                for kw in v:
                    flat[f"kw_{kw}"] = 1
            elif isinstance(v, (int, float)):
                flat[k] = v
            elif isinstance(v, str):
                flat[f"{k}_{v}"] = 1
        return flat


class FileModel(BaseModel):
    pass


class ContentModel(BaseModel):
    def learn(self, features, signal):
        super().learn(features, signal / 10.0 if signal > 1 else signal)
