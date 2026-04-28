"""Feature extraction for BIL models."""
from datetime import datetime


def extract_web_features(url: str, text: str, time_on_page: int = 0,
                         scroll_depth: float = 0.0,
                         bookmarked: bool = False,
                         copy_count: int = 0,
                         word_count: int | None = None) -> tuple[dict, float]:
    """Extract features and implicit signal from a web page visit.

    ``scroll_depth`` is a 0-1 float (max fraction of the page actually scrolled
    through). ``copy_count`` is the number of clipboard copy events on the
    page. ``word_count`` lets the caller pass the browser's own estimate (the
    rendered DOM) instead of recomputing it from ``text``, which is usually a
    truncated snippet.
    """
    from urllib.parse import urlparse
    import yake

    parsed = urlparse(url)
    domain = parsed.netloc

    extractor = yake.KeywordExtractor(lan="en", n=2, top=5)
    keywords = [kw for kw, _ in extractor.extract_keywords(text[:5000])] if text else []

    features = {
        "domain": domain,
        "word_count": word_count if word_count is not None else (len(text.split()) if text else 0),
        "has_equations": any(c in text for c in "\u222b\u2211\u220f\u2202\u2207\u03c7\u03c8\u03c6=") if text else False,
        "top_keywords": keywords,
        "time_of_day": datetime.now().hour,
        "time_on_page": time_on_page,
        "scroll_depth": float(scroll_depth or 0.0),
        "copy_count": int(copy_count or 0),
    }

    signal = 0.0
    if time_on_page > 60:
        signal += 0.2
    if scroll_depth >= 0.7:
        signal += 0.2
    elif scroll_depth >= 0.4:
        signal += 0.1
    if copy_count > 0:
        signal += 0.3
    if bookmarked:
        signal += 0.3

    return features, signal


def extract_file_features(domain: str, subject_codes: list,
                          confidence: float, slug: str) -> dict:
    """Extract features from a FIS classification event."""
    return {
        "domain": domain,
        "subject_primary": subject_codes[0] if subject_codes else "GN",
        "num_subjects": len(subject_codes),
        "confidence": confidence,
        "hour": datetime.now().hour,
        "day_of_week": datetime.now().weekday(),
    }


def extract_clipboard_features(text: str, app: str = "unknown") -> dict:
    """Extract features from a clipboard copy event."""
    import yake
    extractor = yake.KeywordExtractor(lan="en", n=2, top=3)
    keywords = [kw for kw, _ in extractor.extract_keywords(text[:2000])] if text else []
    return {
        "text_keywords": keywords,
        "app": app,
        "hour": datetime.now().hour,
        "text_length": len(text),
    }


def extract_search_result_features(url: str, title: str, snippet: str,
                                   engine: str, score: float,
                                   position: int) -> dict:
    """Extract features from a SearXNG search result for ranking."""
    from urllib.parse import urlparse
    import yake

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    extractor = yake.KeywordExtractor(lan="en", n=2, top=5)
    text = f"{title} {snippet}"
    keywords = [kw for kw, _ in extractor.extract_keywords(text[:1000])] if text.strip() else []

    return {
        "domain": domain,
        "top_keywords": keywords,
        "word_count": len(text.split()),
        "searxng_score": score,
        "original_position": position,
        "engine": engine,
        "time_of_day": datetime.now().hour,
    }
